"""Every fact in a customer reply must cite an FAQ entry that exists and says it."""

import json

from agency import config, llm, offline, services, skill_runner

mod = skill_runner.reply()
FAQ = services.faq()


def draft(*sentences):
    return {"greeting": "Hi Sam,", "sentences": [{"text": t, "type": ty, "faq_ids": ids} for t, ty, ids in sentences],
            "sign_off": "Best regards,\nFernhill Insurance Agency"}


def test_faq_has_thirty_entries():
    assert len(FAQ) == 30
    assert list(FAQ)[0] == "FAQ-01" and list(FAQ)[-1] == "FAQ-30"


def test_supported_fact_is_kept():
    res = mod.check(draft(("We are open on Saturday from 9:00 am to 12:00 pm.", "fact", ["FAQ-01"])), FAQ)
    assert res["flags"] == [] and res["sentences"][0]["faq_ids"] == ["FAQ-01"]
    assert "FAQ-01" not in res["reply_text"]  # citations are for the reviewer, not the customer


def test_uncited_fact_is_replaced_and_flagged():
    res = mod.check(draft(("We are open on Sundays.", "fact", [])), FAQ)
    assert res["sentences"][0]["text"] == mod.CONFIRM
    assert res["flags"][0]["reason"] == "fact with no FAQ citation"


def test_missing_entry_is_replaced():
    res = mod.check(draft(("We are open late on Fridays.", "fact", ["FAQ-99"])), FAQ)
    assert "do not exist" in res["flags"][0]["reason"]


def test_number_not_in_faq_is_replaced():
    res = mod.check(draft(("We are open on Saturday from 9:00 am to 3:00 pm.", "fact", ["FAQ-01"])), FAQ)
    assert res["sentences"][0]["replaced"]
    assert "not in the cited FAQ" in res["flags"][0]["reason"]


def test_wrong_citation_is_replaced():
    res = mod.check(draft(("Your policy covers the full cost of towing.", "fact", ["FAQ-01"])), FAQ)
    assert res["sentences"][0]["replaced"]


def test_fact_dressed_as_courtesy_is_replaced():
    res = mod.check(draft(("Good news, your policy covers this.", "courtesy", [])), FAQ)
    assert res["sentences"][0]["replaced"]


def test_confirm_sentence_cannot_carry_a_fact():
    res = mod.check(draft(("I'll confirm with the team, but flood is covered.", "confirm", [])), FAQ)
    assert res["sentences"][0]["replaced"]
    ok = mod.check(draft(("I'll confirm whether that applies to you with the team.", "confirm", [])), FAQ)
    assert not ok["sentences"][0]["replaced"]
    assert ok["flags"][0]["reason"] == "needs an answer from the team"


def test_every_recorded_reply_cites_real_entries():
    files = sorted((config.FIXTURES_DIR / "customer-reply").glob("*.json"))
    assert len(files) == 10
    for path in files:
        item = json.loads(path.read_text())
        message = (config.ROOT / item["input"]).read_text()
        assert item["key"] == llm.input_key(message)
        res = mod.check(item["response"], FAQ)
        for s in res["sentences"]:
            if s["type"] == "fact":
                assert s["faq_ids"] and all(i in FAQ for i in s["faq_ids"]), (path.name, s)


def test_rule_based_draft_passes_its_own_checks():
    for path in sorted((config.data_dir() / "customer_messages").glob("*.txt")):
        res = mod.check(offline.draft_reply(path.read_text(), FAQ), FAQ)
        assert res["all_facts_cited"], path.name


def test_skill_faq_copy_matches_knowledge():
    assert (config.SKILLS_DIR / "customer-reply" / "reference" / "faq.md").read_text() == \
        (config.KNOWLEDGE_DIR / "faq.md").read_text()
