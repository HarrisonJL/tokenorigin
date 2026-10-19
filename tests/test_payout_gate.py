"""
Direct Mode tests for PayoutGate.

Direct Mode can't run a cross-contract call, so two things are separated here:

- everything that runs BEFORE the read of TokenOrigin (who may call, the amount, the constructor's arguments) is
  tested exactly as written;
- everything that decides on what TokenOrigin says (the subject exists, the token has a decided check, the check
  is fresh, the verdict, the cap) is tested against a stand-in for TokenOrigin that returns the exact shape of
  get_standing(). A test pins that shape to the real contract's output keys, and CONTRACT.md shows the same
  refusals and the approvals on Studio Next, against the real contract, with transaction hashes.
"""

import sys

import pytest

TO_ADDRESS = "0x" + "44" * 20      # never actually called in the pre-call tests
TOKEN = "0xaf88d065e77c8cc2239327c5edb3a432268e5831"
STANDING_KEYS = {"exists", "subject_id", "token", "chain", "symbol", "decimals", "docs_url", "verdict", "check_id", "checked_at",
                 "age_seconds", "status", "listing", "lookalike_of"}


def _deploy(direct_vm, direct_deploy, owner, max_age=86400, cap=1000):
    direct_vm.sender = owner
    return direct_deploy("contracts/payout_gate.py", TO_ADDRESS, max_age, cap)


def standing(**kw):
    base = {"exists": True, "subject_id": "circle-arb", "token": TOKEN, "chain": "arbitrum", "symbol": "USDC", "decimals": 6,
            "docs_url": "https://developers.circle.com/stablecoins/usdc-contract-addresses", "verdict": "CANONICAL", "check_id": 0,
            "checked_at": "2026-10-18T18:00:00+00:00", "age_seconds": 3600, "status": "CURRENT", "listing": [TOKEN], "lookalike_of": None}
    base.update(kw)
    assert set(base) == STANDING_KEYS
    return base


class _View:
    def __init__(self, answers):
        self.answers = answers

    def get_standing(self, subject_id, token):
        return self.answers[(subject_id, token)]


class _Proxy:
    def __init__(self, answers):
        self.answers = answers

    def view(self):
        return _View(self.answers)


@pytest.fixture
def gate(direct_vm, direct_deploy, direct_owner, monkeypatch):
    contract = _deploy(direct_vm, direct_deploy, direct_owner)
    mod = sys.modules["_contract_payout_gate"]
    answers = {}
    monkeypatch.setattr(mod.gl, "get_contract_at", lambda address: _Proxy(answers))
    contract.answers = answers
    return contract


# --- Before the read of TokenOrigin ----------------------------------------------------


def test_config_and_empty_state(direct_vm, direct_deploy, direct_owner):
    g = _deploy(direct_vm, direct_deploy, direct_owner)
    cfg = g.get_config()
    assert cfg["tokenorigin_address"].lower() == TO_ADDRESS and cfg["max_age_seconds"] == 86400
    assert cfg["cap_raw"] == "1000" and cfg["approval_count"] == 0
    assert g.get_total("any", TOKEN) == {"subject_id": "any", "token": TOKEN, "approved_raw": "0", "cap_raw": "1000"}
    assert g.get_approvals(0, 10) == []


@pytest.mark.parametrize("kw,message", [({"max_age": 0}, "max_age_seconds must be positive"), ({"cap": 0}, "cap_raw must be positive")])
def test_a_gate_needs_a_positive_age_and_cap(direct_vm, direct_deploy, direct_owner, kw, message):
    with pytest.raises(Exception, match=message):
        _deploy(direct_vm, direct_deploy, direct_owner, **kw)


def test_only_the_owner_can_approve_a_payout(direct_vm, direct_deploy, direct_owner, direct_alice):
    g = _deploy(direct_vm, direct_deploy, direct_owner)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="only the owner can approve payouts"):
        g.approve("circle-arb", TOKEN, 100)


def test_a_zero_amount_is_rejected_before_any_cross_contract_call(direct_vm, direct_deploy, direct_owner):
    g = _deploy(direct_vm, direct_deploy, direct_owner)
    with pytest.raises(Exception, match="amount must be positive"):
        g.approve("circle-arb", TOKEN, 0)


# --- On what TokenOrigin says (against a stand-in with get_standing's exact shape) ---------


def test_the_issuers_own_token_is_approved_and_recorded(gate, direct_owner):
    gate.answers[("circle-arb", TOKEN)] = standing()
    gate.approve("circle-arb", TOKEN, 400)
    assert gate.get_total("circle-arb", TOKEN) == {"subject_id": "circle-arb", "token": TOKEN, "approved_raw": "400", "cap_raw": "1000"}
    (a,) = gate.get_approvals(0, 10)
    # the log shows which issuer page and chain the approval relied on
    assert (a["subject_id"], a["token"], a["chain"], a["symbol"], a["amount_raw"]) == ("circle-arb", TOKEN, "arbitrum", "USDC", "400")
    assert a["docs_url"] == "https://developers.circle.com/stablecoins/usdc-contract-addresses"
    assert a["approved_by"].lower() == "0x" + direct_owner.hex() and a["approved_at"].count(":") >= 2
    assert gate.get_config()["approval_count"] == 1


def test_the_token_is_looked_up_in_any_case_and_recorded_lowercase(gate):
    upper = "0xAF88D065E77C8CC2239327C5EDB3A432268E5831"
    gate.answers[("circle-arb", upper)] = standing()
    gate.approve("circle-arb", upper, 5)
    assert gate.get_approvals(0, 1)[0]["token"] == TOKEN and gate.get_total("circle-arb", upper)["approved_raw"] == "5"


@pytest.mark.parametrize("verdict", ["DEPRECATED", "NOT_ISSUER_ISSUED", "NOT_LISTED", "LOOKALIKE", "NOT_A_TOKEN", "UNDETERMINED", "something-new"])
def test_any_other_verdict_gets_nothing(gate, verdict):
    gate.answers[("circle-arb", TOKEN)] = standing(verdict=verdict)
    with pytest.raises(Exception, match=f"is {verdict}, not CANONICAL"):
        gate.approve("circle-arb", TOKEN, 1)
    assert gate.get_config()["approval_count"] == 0


def test_a_subject_that_does_not_exist_or_a_token_never_checked_gets_nothing(gate):
    gate.answers[("ghost", TOKEN)] = {"exists": False, "subject_id": "ghost"}
    with pytest.raises(Exception, match="TokenOrigin has no such subject"):
        gate.approve("ghost", TOKEN, 1)
    gate.answers[("circle-arb", TOKEN)] = standing(verdict="NO_CHECK", check_id=None, checked_at=None, age_seconds=None, status=None, listing=[])
    with pytest.raises(Exception, match="no decided check of .* yet"):
        gate.approve("circle-arb", TOKEN, 1)


@pytest.mark.parametrize("age,ok", [(0, True), (86400, True), (86401, False), (10 ** 9, False), (-1, False), (None, False)])
def test_the_check_must_be_fresh_but_not_from_the_future(gate, age, ok):
    gate.answers[("circle-arb", TOKEN)] = standing(age_seconds=age)
    if ok:
        gate.approve("circle-arb", TOKEN, 1)
    else:
        with pytest.raises(Exception, match="seconds old"):
            gate.approve("circle-arb", TOKEN, 1)


def test_a_subjects_approvals_are_capped_in_total_per_token(gate):
    other = "0x" + "99" * 20
    gate.answers[("circle-arb", TOKEN)] = standing()
    gate.answers[("circle-arb", other)] = standing(token=other)
    gate.approve("circle-arb", TOKEN, 600)
    gate.approve("circle-arb", TOKEN, 400)                      # exactly the cap
    with pytest.raises(Exception, match="past the cap 1000"):
        gate.approve("circle-arb", TOKEN, 1)
    gate.approve("circle-arb", other, 1000)                     # another token has its own room
    assert gate.get_total("circle-arb", TOKEN)["approved_raw"] == "1000" and gate.get_total("circle-arb", other)["approved_raw"] == "1000"
    assert [a["amount_raw"] for a in gate.get_approvals(0, 10)] == ["1000", "400", "600"]      # newest first
    assert [a["amount_raw"] for a in gate.get_approvals(1, 1)] == ["400"]


def test_a_refusal_changes_nothing(gate):
    gate.answers[("circle-arb", TOKEN)] = standing(verdict="LOOKALIKE")
    with pytest.raises(Exception):
        gate.approve("circle-arb", TOKEN, 5)
    assert gate.get_total("circle-arb", TOKEN)["approved_raw"] == "0" and gate.get_approvals(0, 10) == []


def test_paging_is_capped_at_fifty(gate):
    gate.answers[("circle-arb", TOKEN)] = standing()
    for _ in range(52):
        gate.approve("circle-arb", TOKEN, 1)
    assert len(gate.get_approvals(0, 1000)) == 50 and gate.get_approvals(60, 5) == []
    assert len(gate.get_approvals(50, 10)) == 2
