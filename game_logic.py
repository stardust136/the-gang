import random
from typing import List, Dict, Optional
from treys import Evaluator, Card as TreysCard, Deck as TreysDeck

# --- Constants ---
SUIT_MAP = {'s': '♠', 'h': '♥', 'd': '♦', 'c': '♣'}

PHASES = ['PREFLOP', 'FLOP', 'TURN', 'RIVER', 'SHOWDOWN', 'RESULT']
CHIP_COLORS = {
    'PREFLOP': 'White',
    'FLOP': 'Yellow',
    'TURN': 'Orange',
    'RIVER': 'Red',
    'SHOWDOWN': 'Red',
    'RESULT': 'Red'
}


class Player:
    def __init__(self, sid, name):
        self.sid = sid
        self.name = name
        self.hand_ints: List[int] = []
        self.hand_str: List[dict] = []
        self.chip: Optional[int] = None
        self.chip_history: List[dict] = []
        self.is_settled: bool = False

    def to_dict(self, include_hand=False):
        return {
            'sid': self.sid,
            'name': self.name,
            'hand': self.hand_str if include_hand else [],
            'chip': self.chip,
            'chip_history': self.chip_history,
            'is_settled': self.is_settled
        }


class Game:
    def __init__(self):
        self.players: Dict[str, Player] = {}
        self.community_ints: List[int] = []
        self.community_str: List[dict] = []
        self.evaluator = Evaluator()
        self.deck = None
        self.phase_index = 0
        self.chips_available = []
        self.game_started = False
        self.heist_result = ""
        self.vaults = 0
        self.alarms = 0

    def _format_card(self, card_int):
        c_str = TreysCard.int_to_str(card_int)
        rank = c_str[0].replace('T', '10')
        suit = SUIT_MAP.get(c_str[1], c_str[1])
        return {'rank': rank, 'suit': suit, 'str': rank + suit}

    def change_player_name(self, sid, new_name):
        new_name = new_name.strip()
        if not new_name:
            return False, "Name cannot be empty."

        # Check for duplicate names (case-insensitive)
        for p in self.players.values():
            if p.sid != sid and p.name.lower() == new_name.lower():
                return False, "Name already taken."

        if sid in self.players:
            self.players[sid].name = new_name
            return True, "Name changed."

        return False, "Player not found."

    def start_game(self):
        if len(self.players) < 3: return False

        if self.vaults >= 3 or self.alarms >= 3:
            self.vaults = 0
            self.alarms = 0

        self.deck = TreysDeck()
        self.game_started = True
        self.phase_index = 0
        self.community_ints = []
        self.community_str = []
        self.heist_result = ""

        for player in self.players.values():
            cards = self.deck.draw(2)
            player.hand_ints = cards
            player.hand_str = [
                self._format_card(cards[0]),
                self._format_card(cards[1])
            ]
            player.chip = None
            player.chip_history = []
            player.is_settled = False

        self._setup_phase_chips()
        return True

    def _setup_phase_chips(self):
        num_players = len(self.players)
        self.chips_available = list(range(1, num_players + 1))
        for p in self.players.values():
            p.chip = None
            p.is_settled = False

    def next_phase(self):
        if self.phase_index >= len(PHASES) - 1: return

        current_color = CHIP_COLORS[PHASES[self.phase_index]]
        for p in self.players.values():
            if p.chip is not None:
                p.chip_history.append({'color': current_color, 'value': p.chip})

        self.phase_index += 1
        phase = PHASES[self.phase_index]

        if phase in ['FLOP', 'TURN', 'RIVER']:
            count = 3 if phase == 'FLOP' else 1
            self._draw_community(count)
            self._setup_phase_chips()
        elif phase == 'SHOWDOWN':
            self.evaluate_showdown()
            self.phase_index += 1

    def _draw_community(self, count):
        new_cards = self.deck.draw(count)
        self.community_ints.extend(new_cards)
        for c in new_cards:
            self.community_str.append(self._format_card(c))

    def evaluate_showdown(self):
        active_players = [p for p in self.players.values() if p.chip is not None]
        active_players.sort(key=lambda p: p.chip)

        previous_score = 999999
        mistake_made = False
        result_log = []

        for p in active_players:
            score = self.evaluator.evaluate(self.community_ints, p.hand_ints)
            rank_class = self.evaluator.get_rank_class(score)
            class_str = self.evaluator.class_to_string(rank_class)

            if score > previous_score:
                mistake_made = True
                result_log.append(f"❌ {p.name} ({p.chip}★): {class_str} (Weaker!)")
            else:
                result_log.append(f"✅ {p.name} ({p.chip}★): {class_str}")

            previous_score = score

        if mistake_made:
            self.alarms += 1
            self.heist_result = f"ALARM TRIPPED! 🚨 ({self.alarms}/3)<br>" + "<br>".join(result_log)
        else:
            self.vaults += 1
            self.heist_result = f"HEIST SUCCESS! 💰 ({self.vaults}/3)<br>" + "<br>".join(result_log)

        if self.alarms >= 3:
            self.heist_result += "<br><br><b>GAME OVER! THE POLICE ARRIVED! 🚓</b>"
        elif self.vaults >= 3:
            self.heist_result += "<br><br><b>YOU WIN! RETIRE RICH! 💎</b>"

    def handle_take_chip(self, player_sid, chip_value, source_sid):
        actor = self.players.get(player_sid)
        if not actor or actor.is_settled: return False

        if actor.chip is not None:
            self.chips_available.append(actor.chip)
            actor.chip = None

        if source_sid == "center":
            if chip_value in self.chips_available:
                self.chips_available.remove(chip_value)
                actor.chip = chip_value
            else:
                return False
        else:
            victim = self.players.get(source_sid)
            if victim and victim.chip == chip_value:
                victim.chip = None
                victim.is_settled = False
                actor.chip = chip_value
            else:
                return False
        return True

    def handle_return_chip(self, player_sid):
        player = self.players.get(player_sid)
        if not player or player.is_settled or player.chip is None: return False
        self.chips_available.append(player.chip)
        self.chips_available.sort()
        player.chip = None
        return True

    def toggle_settle(self, player_sid):
        player = self.players.get(player_sid)
        if not player or player.chip is None: return False

        player.is_settled = not player.is_settled

        active_count = len(self.players)
        settled_with_chips = sum(1 for p in self.players.values() if p.is_settled and p.chip is not None)

        if settled_with_chips == active_count:
            self.next_phase()

        return True

    def get_state(self, for_player_sid):
        safe_phase = PHASES[self.phase_index] if self.phase_index < len(PHASES) else "RESULT"
        show_all = (safe_phase == 'RESULT')

        return {
            'phase': safe_phase if self.game_started else "LOBBY",
            'chip_color': CHIP_COLORS.get(safe_phase, 'Red'),
            'community_cards': self.community_str,
            'chips_available': self.chips_available,
            'players': [p.to_dict(include_hand=(p.sid == for_player_sid or show_all)) for p in self.players.values()],
            'me': self.players[for_player_sid].to_dict(include_hand=True) if for_player_sid in self.players else None,
            'result_message': self.heist_result,
            'vaults': self.vaults,
            'alarms': self.alarms
        }