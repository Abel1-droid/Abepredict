import os
import json
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView

import predictor
from fixture_sync import sync_fixtures


class AbepredictApp(App):
    title = "Abepredict"

    def build(self):
        os.makedirs(self.user_data_dir, exist_ok=True)
        os.chdir(self.user_data_dir)

        self.cache_file = os.path.join(self.user_data_dir, "predictions.json")
        self.results = []

        root = BoxLayout(orientation="vertical", padding=12, spacing=10)

        header = Label(
            text="[b]ABEPREDICT[/b]\nEnglish Football Predictions",
            markup=True,
            font_size="23sp",
            size_hint_y=None,
            height=75
        )
        root.add_widget(header)

        controls = BoxLayout(size_hint_y=None, height=48, spacing=8)

        self.league_filter = Spinner(
            text="All leagues",
            values=(
                "All leagues",
                "Championship",
                "League One",
                "League Two",
                "National League"
            ),
            size_hint_x=0.65
        )
        self.league_filter.bind(text=lambda *_: self.render_results())
        controls.add_widget(self.league_filter)

        self.refresh_button = Button(
            text="Refresh",
            size_hint_x=0.35
        )
        self.refresh_button.bind(on_press=self.refresh)
        controls.add_widget(self.refresh_button)

        root.add_widget(controls)

        self.status = Label(
            text="Loading saved predictions...",
            size_hint_y=None,
            height=42
        )
        root.add_widget(self.status)

        scroll = ScrollView()
        self.cards = BoxLayout(
            orientation="vertical",
            spacing=10,
            size_hint_y=None,
            padding=4
        )
        self.cards.bind(minimum_height=self.cards.setter("height"))
        scroll.add_widget(self.cards)
        root.add_widget(scroll)

        self.load_cache()
        self.render_results()
        Clock.schedule_once(lambda dt: self.refresh(), 1)

        return root

    def load_cache(self):
        try:
            with open(self.cache_file, encoding="utf-8") as f:
                self.results = json.load(f)
        except Exception:
            self.results = []

    def refresh(self, *_):
        self.refresh_button.disabled = True
        self.status.text = "Updating fixtures and calculating predictions..."

        threading.Thread(
            target=self.calculate,
            daemon=True
        ).start()

    def calculate(self):
        try:
            results = predictor.load_results()

            try:
                sync_fixtures()
            except Exception:
                pass

            fixtures = predictor.read_fixtures()
            predictions = []

            for fixture in fixtures:
                matches = results[fixture["div"]]
                relevant = [
                    m for m in matches
                    if m["date"] < fixture["date"]
                ]

                stats = predictor.build_stats(relevant)
                home = stats.get(fixture["home"])
                away = stats.get(fixture["away"])

                if not home or not away:
                    continue

                if len(home["all"]) < 3 or len(away["all"]) < 3:
                    continue

                league_home = predictor.average(
                    [m["hg"] for m in relevant], 1.4
                )
                league_away = predictor.average(
                    [m["ag"] for m in relevant], 1.1
                )

                hxg, axg = predictor.expected_goals(
                    home, away, league_home, league_away
                )

                markets = predictor.calculate_probabilities(hxg, axg)
                best = max(markets, key=markets.get)

                predictions.append({
                    "date": fixture["date"].isoformat(),
                    "league": predictor.LEAGUES[fixture["div"]],
                    "home": fixture["home"],
                    "away": fixture["away"],
                    "home_xg": round(hxg, 2),
                    "away_xg": round(axg, 2),
                    "best_market": best,
                    "best_probability": round(markets[best] * 100, 1),
                    "markets": {
                        name: round(value * 100, 1)
                        for name, value in markets.items()
                    }
                })

            predictions.sort(
                key=lambda item: item["best_probability"],
                reverse=True
            )
            predictions = predictions[:10]

            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(predictions, f)

            Clock.schedule_once(
                lambda dt: self.finish_refresh(predictions, None)
            )

        except Exception as error:
            Clock.schedule_once(
                lambda dt: self.finish_refresh(None, str(error))
            )

    def finish_refresh(self, predictions, error):
        self.refresh_button.disabled = False

        if error:
            self.status.text = "Update failed. Showing saved predictions."
            self.load_cache()
        else:
            self.results = predictions
            self.status.text = (
                f"{len(predictions)} selections available"
                if predictions else
                "No upcoming matches available from the fixture source."
            )

        self.render_results()

    def render_results(self):
        self.cards.clear_widgets()

        selected = self.league_filter.text
        shown = [
            item for item in self.results
            if selected == "All leagues" or item["league"] == selected
        ]

        if not shown:
            self.cards.add_widget(Label(
                text="No predictions to display yet.\n"
                     "Try Refresh when new fixtures are available.",
                size_hint_y=None,
                height=100
            ))
            return

        for index, item in enumerate(shown, 1):
            card = BoxLayout(
                orientation="vertical",
                padding=12,
                spacing=5,
                size_hint_y=None
            )
            card.bind(minimum_height=card.setter("height"))

            card.add_widget(Label(
                text=f"[b]#{index}  {item['home']} vs {item['away']}[/b]",
                markup=True,
                size_hint_y=None,
                height=38
            ))

            card.add_widget(Label(
                text=f"{item['league']}  |  {item['date']}",
                size_hint_y=None,
                height=28
            ))

            card.add_widget(Label(
                text=f"Expected goals: {item['home_xg']} - {item['away_xg']}",
                size_hint_y=None,
                height=28
            ))

            card.add_widget(Label(
                text=f"[b]{item['best_market']}: "
                     f"{item['best_probability']}%[/b]",
                markup=True,
                size_hint_y=None,
                height=32
            ))

            market_lines = [
                f"{name}: {probability}%"
                for name, probability in sorted(
                    item["markets"].items(),
                    key=lambda pair: pair[1],
                    reverse=True
                )
            ]

            card.add_widget(Label(
                text="\n".join(market_lines),
                size_hint_y=None,
                height=250,
                halign="left",
                valign="middle"
            ))

            self.cards.add_widget(card)

    def on_stop(self):
        pass


if __name__ == "__main__":
    AbepredictApp().run()
