# New Cards Tracker

Anki add-on that shows how many **cards** you added each day on the main deck browser, compared to a daily target (default **10**).

Inspired by [Review Heatmap](https://github.com/glutanimate/review-heatmap/wiki) for main-screen placement; uses a week/month bar chart with target highlighting instead of a year calendar.

**License:** [MIT](LICENSE)

## Features

- Chart on the deck browser (main screen)
- **Week** and **Month** views with prev/next pagination
- Bars colored by whether you met your daily target
- Today summary (`N / target`) and target streak
- Click a day to open the Browser on cards added that Anki day
- Options under **Tools → New Cards Tracker Options…**

## Requirements

- Anki 23.10+ (Qt6)

## Install

### From source

1. Quit Anki.
2. Copy or symlink the `new_cards_added_tracker` folder into your Anki `addons21` directory:

```bash
# macOS example
ln -s "/path/to/repo/new_cards_added_tracker" \
  "$HOME/Library/Application Support/Anki2/addons21/new_cards_added_tracker"
```

3. Start Anki. The chart appears on the main deck screen.

## Configuration

| Key | Default | Meaning |
|-----|---------|---------|
| `daily_target` | `10` | Cards to add per day |
| `default_view` | `"week"` | `"week"` or `"month"` |
| `show_on_deck_browser` | `true` | Show chart on main screen |

Edit via **Tools → New Cards Tracker Options…**, or Anki’s add-on Config dialog.

## How counts work

- Counts **cards** by creation time (`cards.id`), matching Anki’s `added:` search
- Day boundaries follow Anki’s **Next day starts at** rollover (`day_cutoff`)
