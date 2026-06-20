#!/usr/bin/env python3
"""RAPP Commons — Texas Hold'em poker engine (pure stdlib, additive).

This is the canonical, importable engine for the poker room in commons.html.
The browser room mirrors this engine's ACTION SHAPE (rapp-poker-action/1.0) and
its hand ranking exactly, so an in-browser hand and a server-replayed hand agree.

Contract used by the acceptance tests (tests/test_data.py::poker_engine):
  - a hand-rank function `rank_hand` (alias `evaluate`) that ranks a royal flush
    above a pair (higher tuple == stronger hand).

Cards are 2-char strings: rank in "23456789TJQKA", suit in "shdc".
  e.g. "As" = ace of spades, "Td" = ten of diamonds.

Every poker ACTION (post/check/bet/call/raise/fold, plus deal commit/reveal) is a
signed `rapp-poker-action/1.0` record. This module builds the canonical action
body; signing is done by the caller (per-bot / per-player rappid keypair) — the
engine NEVER signs as a human and NEVER mints identity itself.
"""
from __future__ import annotations
import json, hashlib, itertools
from typing import List, Tuple, Dict, Any, Optional

RANKS = "23456789TJQKA"
SUITS = "shdc"
RANK_VAL = {r: i + 2 for i, r in enumerate(RANKS)}  # '2'->2 .. 'A'->14

# Hand category constants (higher == stronger). Used as the first tuple element.
HIGH_CARD       = 0
PAIR            = 1
TWO_PAIR        = 2
THREE_KIND      = 3
STRAIGHT        = 4
FLUSH           = 5
FULL_HOUSE      = 6
FOUR_KIND       = 7
STRAIGHT_FLUSH  = 8

CATEGORY_NAME = {
    HIGH_CARD: "high card", PAIR: "pair", TWO_PAIR: "two pair",
    THREE_KIND: "three of a kind", STRAIGHT: "straight", FLUSH: "flush",
    FULL_HOUSE: "full house", FOUR_KIND: "four of a kind",
    STRAIGHT_FLUSH: "straight flush",
}


def full_deck() -> List[str]:
    """A standard 52-card deck in canonical order."""
    return [r + s for r in RANKS for s in SUITS]


def _ranks_suits(cards):
    vals = sorted((RANK_VAL[c[0]] for c in cards), reverse=True)
    suits = [c[1] for c in cards]
    return vals, suits


def _straight_high(vals_set) -> Optional[int]:
    """Return the high card of a straight in the given set of rank values, else None.
    Handles the wheel (A-2-3-4-5) where the ace plays low and the straight high is 5."""
    vs = set(vals_set)
    if 14 in vs:
        vs = vs | {1}  # ace can be low
    run = 0
    high = None
    for v in range(14, 0, -1):
        if v in vs:
            run += 1
            if run == 1:
                high = v
            if run >= 5:
                return high
        else:
            run = 0
            high = None
    return None


def _rank_five(cards: List[str]) -> Tuple:
    """Rank exactly 5 cards. Returns a comparable tuple (category, *tiebreakers)."""
    vals, suits = _ranks_suits(cards)
    counts: Dict[int, int] = {}
    for v in vals:
        counts[v] = counts.get(v, 0) + 1
    # order ranks by (count desc, value desc) for tiebreakers
    by_count = sorted(counts.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
    count_shape = tuple(c for _, c in by_count)
    ordered_vals = tuple(v for v, _ in by_count)

    is_flush = len(set(suits)) == 1
    straight_high = _straight_high(vals)

    if is_flush and straight_high is not None:
        return (STRAIGHT_FLUSH, straight_high)
    if count_shape == (4, 1):
        return (FOUR_KIND,) + ordered_vals
    if count_shape == (3, 2):
        return (FULL_HOUSE,) + ordered_vals
    if is_flush:
        return (FLUSH,) + tuple(sorted(vals, reverse=True))
    if straight_high is not None:
        return (STRAIGHT, straight_high)
    if count_shape == (3, 1, 1):
        return (THREE_KIND,) + ordered_vals
    if count_shape == (2, 2, 1):
        return (TWO_PAIR,) + ordered_vals
    if count_shape == (2, 1, 1, 1):
        return (PAIR,) + ordered_vals
    return (HIGH_CARD,) + tuple(sorted(vals, reverse=True))


def rank_hand(cards: List[str]) -> Tuple:
    """Rank a poker hand of 5, 6, or 7 cards. Returns a comparable tuple where a
    LARGER tuple is a STRONGER hand. With >5 cards, returns the best 5-card combo.

    >>> rank_hand(["As","Ks","Qs","Js","Ts"]) > rank_hand(["2h","2d","5s","9c","Kh"])
    True
    """
    cards = list(cards)
    if len(cards) < 5:
        raise ValueError("need at least 5 cards to rank a poker hand")
    if len(cards) == 5:
        return _rank_five(cards)
    best = None
    for combo in itertools.combinations(cards, 5):
        r = _rank_five(list(combo))
        if best is None or r > best:
            best = r
    return best


# Back-compat alias expected by the test contract.
evaluate = rank_hand


def best_hand_name(cards: List[str]) -> str:
    return CATEGORY_NAME[rank_hand(cards)[0]]


def compare(a_cards: List[str], b_cards: List[str]) -> int:
    """+1 if a beats b, -1 if b beats a, 0 tie."""
    ra, rb = rank_hand(a_cards), rank_hand(b_cards)
    return (ra > rb) - (ra < rb)


# ── Commit–reveal deck (provably-fair shuffle) ────────────────────────────────
def deck_commitment(deck: List[str], nonce: str) -> str:
    """SHA-256 commitment to a shuffled deck order + a secret nonce. The dealer
    publishes this BEFORE the hand; revealing (deck, nonce) at showdown proves the
    deck was fixed in advance (no card-switching). Mirrored byte-for-byte in JS."""
    body = json.dumps({"deck": deck, "nonce": nonce}, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(body.encode()).hexdigest()


def verify_commitment(deck: List[str], nonce: str, commitment: str) -> bool:
    return deck_commitment(deck, nonce) == commitment


# ── Signed action shape (rapp-poker-action/1.0) ───────────────────────────────
LEGAL_ACTIONS = {"post", "check", "bet", "call", "raise", "fold", "deal", "reveal"}


def action_body(hand_id: str, seq: int, seat: int, actor_rappid: str,
                action: str, amount: int = 0, ts: Optional[str] = None,
                extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build the canonical (unsigned) body of a poker action. The CALLER signs the
    canonical JSON of this body with the seat's OWN rappid keypair and attaches the
    signature as `sig` (+ `pub`). The engine never signs.

    This is the EXACT shape mirrored by the browser poker room so a hand played in
    the world can be replayed/verified here."""
    if action not in LEGAL_ACTIONS:
        raise ValueError(f"illegal action {action!r}; legal: {sorted(LEGAL_ACTIONS)}")
    body = {
        "schema": "rapp-poker-action/1.0",
        "hand_id": hand_id,
        "seq": int(seq),
        "seat": int(seat),
        "from": actor_rappid,            # per-seat rappid (bot or player), NOT a human
        "action": action,
        "amount": int(amount),
        "ts": ts,
    }
    if extra:
        body.update(extra)
    return body


def canonical(obj: Any) -> str:
    """Deterministic JSON used as the signing pre-image (matches the JS canonicalJSON)."""
    return json.dumps(obj, separators=(",", ":"), sort_keys=True)


# ── Minimal Texas Hold'em loop (deterministic, for replay/verification) ───────
class HoldemHand:
    """A single Texas Hold'em hand over N seats. Drives a deal from a fixed
    (already shuffled + committed) deck and tracks the betting record as a list of
    action bodies. Signing is external. This is a *reference* loop — the browser
    room runs the interactive version and emits the same action bodies."""

    def __init__(self, hand_id: str, seats: List[Dict[str, Any]], deck: List[str],
                 small_blind: int = 1, big_blind: int = 2):
        self.hand_id = hand_id
        self.seats = seats              # [{"seat":0,"rappid":...,"chips":1000}, ...]
        self.deck = list(deck)
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.holes: Dict[int, List[str]] = {}
        self.board: List[str] = []
        self.actions: List[Dict[str, Any]] = []
        self._i = 0
        self._seq = 0

    def _draw(self) -> str:
        c = self.deck[self._i]; self._i += 1; return c

    def deal_holes(self):
        for s in self.seats:
            self.holes[s["seat"]] = [self._draw(), self._draw()]

    def deal_flop(self):
        self._draw()  # burn
        self.board += [self._draw(), self._draw(), self._draw()]

    def deal_turn(self):
        self._draw(); self.board.append(self._draw())

    def deal_river(self):
        self._draw(); self.board.append(self._draw())

    def record(self, seat: int, rappid: str, action: str, amount: int = 0,
               ts: Optional[str] = None, extra=None) -> Dict[str, Any]:
        self._seq += 1
        b = action_body(self.hand_id, self._seq, seat, rappid, action, amount, ts, extra)
        self.actions.append(b)
        return b

    def showdown(self, contenders: Optional[List[int]] = None) -> Dict[str, Any]:
        """Return the winning seat(s) among contenders (default: all seated)."""
        if contenders is None:
            contenders = [s["seat"] for s in self.seats]
        best_seat, best_rank = None, None
        for seat in contenders:
            seven = self.holes[seat] + self.board
            r = rank_hand(seven)
            if best_rank is None or r > best_rank:
                best_rank, best_seat = r, seat
        winners = [s for s in contenders
                   if rank_hand(self.holes[s] + self.board) == best_rank]
        return {"winners": winners, "rank": best_rank,
                "category": CATEGORY_NAME[best_rank[0]], "board": list(self.board)}


if __name__ == "__main__":
    # tiny self-check
    royal = ["As", "Ks", "Qs", "Js", "Ts"]
    pair  = ["2h", "2d", "5s", "9c", "Kh"]
    assert rank_hand(royal) > rank_hand(pair), "royal flush must beat a pair"
    assert evaluate is rank_hand
    d = full_deck(); assert len(d) == 52 and len(set(d)) == 52
    c = deck_commitment(d, "nonce-123")
    assert verify_commitment(d, "nonce-123", c)
    print("poker engine self-check OK:", best_hand_name(royal), ">", best_hand_name(pair))
