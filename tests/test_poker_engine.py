#!/usr/bin/env python3
"""Tests for games/poker/engine.py -- ranking, commit-reveal, signing, play."""

import os
import sys
import unittest

# Make the brainstem repo root importable so `games.poker.engine` resolves.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from games.poker import engine as E  # noqa: E402


class TestRankHand(unittest.TestCase):
    def test_category_ordering(self):
        royal = E.rank_hand("As Ks Qs Js Ts".split())
        sflush = E.rank_hand("9s 8s 7s 6s 5s".split())
        quads = E.rank_hand("9c 9d 9h 9s Kc".split())
        boat = E.rank_hand("9c 9d 9h Kc Ks".split())
        flush = E.rank_hand("As Js 9s 6s 3s".split())
        straight = E.rank_hand("9c 8d 7h 6s 5c".split())
        trips = E.rank_hand("9c 9d 9h Kc 3s".split())
        twopair = E.rank_hand("9c 9d Kc Ks 3s".split())
        pair = E.rank_hand("As Ad 7c 4h 2s".split())
        high = E.rank_hand("As Kd 9c 7h 2s".split())
        order = [royal, sflush, quads, boat, flush, straight, trips,
                 twopair, pair, high]
        for a, b in zip(order, order[1:]):
            self.assertGreater(a, b, (a, b))

    def test_evaluate_alias(self):
        self.assertEqual(E.evaluate("As Ks Qs Js Ts".split()),
                         E.rank_hand("As Ks Qs Js Ts".split()))

    def test_seven_card_best_five(self):
        r = E.rank_hand("As Ks Qs Js Ts 2d 3c".split())
        self.assertEqual(r[0], E.ROYAL_FLUSH)

    def test_wheel_straight(self):
        r = E.rank_hand("Ah 2d 3c 4s 5h".split())
        self.assertEqual(r[0], E.STRAIGHT)
        self.assertEqual(r[1], 5)  # 5-high, ace plays low

    def test_six_card_hand(self):
        r = E.rank_hand("Ah Ad Ac 5h 5d 2c".split())
        self.assertEqual(r[0], E.FULL_HOUSE)

    def test_min_cards(self):
        with self.assertRaises(ValueError):
            E.rank_hand("As Ks Qs Js".split())


class TestCommitReveal(unittest.TestCase):
    def test_deck_has_52_unique(self):
        d = E.Deck(salt="x")
        seen = set()
        for _ in range(52):
            seen.add(str(d.deal()))
        self.assertEqual(len(seen), 52)

    def test_commit_verifies(self):
        d = E.Deck(salt="seedy")
        self.assertTrue(E.Deck.verify(d.reveal()))

    def test_tamper_detected(self):
        d = E.Deck(salt="seedy")
        proof = d.reveal()
        proof = dict(proof)
        proof["order"] = list(proof["order"])
        proof["order"][0], proof["order"][1] = proof["order"][1], proof["order"][0]
        self.assertFalse(E.Deck.verify(proof))

    def test_commit_published_before_deal(self):
        d = E.Deck()
        self.assertTrue(d.commit)
        d.deal()
        # commit must not change as cards are dealt
        self.assertEqual(d.commit, d.reveal()["commit"])


class TestSignedActions(unittest.TestCase):
    def test_canonical_schema(self):
        rid = E.mint_rappid("poker", "bot-a")
        a = E.canonical_action("t1", 2, rid, "raise", 40)
        self.assertEqual(a["schema"], E.ACTION_SCHEMA)
        for k in ("table", "seat", "from", "ts", "act", "amount", "sig"):
            self.assertIn(k, a)
        self.assertIsNone(a["sig"])

    def test_sign_and_verify(self):
        rid = E.mint_rappid("poker", "bot-a")
        a = E.canonical_action("t1", 0, rid, "call", 10)
        s = E.sign_action(a, "secret")
        self.assertTrue(s["sig"].startswith("hmac-sha256:"))
        self.assertTrue(E.verify_action(s, "secret"))

    def test_wrong_secret_fails(self):
        rid = E.mint_rappid("poker", "bot-a")
        s = E.sign_action(E.canonical_action("t1", 0, rid, "fold"), "secret")
        self.assertFalse(E.verify_action(s, "nope"))

    def test_identity_binding(self):
        # a signature minted under one rappid must not verify if `from` swapped
        rid = E.mint_rappid("poker", "bot-a")
        s = E.sign_action(E.canonical_action("t1", 0, rid, "bet", 20), "secret")
        s = dict(s)
        s["from"] = E.mint_rappid("poker", "bot-b")
        self.assertFalse(E.verify_action(s, "secret"))

    def test_human_signature_refused(self):
        with self.assertRaises(ValueError):
            E.canonical_action("t1", 0, "human:kody", "fold")

    def test_unsignable_refused(self):
        rid = E.mint_rappid("poker", "bot-a")
        with self.assertRaises(ValueError):
            E.sign_action(E.canonical_action("t1", 0, rid, "fold"), "")


class TestTablePlay(unittest.TestCase):
    def _det_deck(self):
        seed = [12345]

        def rng(n):
            seed[0] = (seed[0] * 1103515245 + 12345) & 0x7FFFFFFF
            return seed[0] % n
        return E.Deck(rng=rng)

    def test_six_seats_max(self):
        t = E.Table()
        for i in range(6):
            t.seat_player(f"B{i}")
        with self.assertRaises(RuntimeError):
            t.seat_player("overflow")

    def test_full_hand_has_winner_and_conserves_chips(self):
        t = E.Table(strategy=E.calling_station_bot)
        for i in range(6):
            t.seat_player(f"Bot{i}", chips=1000)
        start = sum(p.chips for p in t.players)
        hand = t.play_hand(deck=self._det_deck())
        self.assertTrue(hand.winners)
        self.assertEqual(sum(p.chips for p in t.players), start)

    def test_action_log_signed_and_append_only(self):
        t = E.Table(strategy=E.calling_station_bot)
        for i in range(4):
            t.seat_player(f"Bot{i}", chips=500)
        hand = t.play_hand(deck=self._det_deck())
        self.assertTrue(hand.log)
        for act in hand.log:
            self.assertTrue(act["sig"])
            self.assertTrue(act["sig"].startswith("hmac-sha256:"))
            self.assertTrue(act["from"].startswith("rappid:"))
        # appended to the table's running log, in order
        self.assertEqual(t.action_log[:len(hand.log)], hand.log)

    def test_fold_to_one_winner(self):
        t = E.Table(strategy=E.fold_or_check_bot, big_blind=10)
        # seat a raiser-free table; default bot folds to any real bet,
        # but with only blinds and checks someone still wins.
        for i in range(3):
            t.seat_player(f"Bot{i}", chips=1000)
        hand = t.play_hand(deck=self._det_deck())
        self.assertTrue(hand.winners)

    def test_deck_reveal_after_play(self):
        t = E.Table(strategy=E.calling_station_bot)
        for i in range(2):
            t.seat_player(f"Bot{i}")
        hand = t.play_hand(deck=self._det_deck())
        self.assertTrue(E.Deck.verify(hand.reveal_proof()))


class TestSelfTest(unittest.TestCase):
    def test_module_self_test_passes(self):
        self.assertTrue(E._self_test())


if __name__ == "__main__":
    unittest.main()
