# Start Trading Bot UI

Launch the multi-terminal dashboard for monitoring BTC, ETH, and SOL markets.

---

## Step 1: Select Strategy

Ask the user which strategy to use:

> **Which strategy would you like to use?**

Use the AskQuestion tool:

```
AskQuestion:
  title: "Strategy Selection"
  questions:
    - id: "strategy"
      prompt: "Select a strategy for signal generation:"
      options:
        - id: "momentum_based"
          label: "momentum_based (default)"
        - id: "rsi_based"
          label: "rsi_based"
        - id: "multi_signal"
          label: "multi_signal"
```

Store the selected strategy for use in commands.

---

## Step 2: Present Terminal Commands

Based on the selected strategy, present the commands to run:

> **Multi-Terminal Dashboard Setup**
>
> You need to run these commands in **4 separate terminal windows**.
> Copy each command and run in its own terminal.
>
> ---
>
> **Terminal 1: Data Server** (run first, keep running)
>
> ```bash
> cd /Users/ofers/Documents/trading-bot && python -m bot.ui.cli --server --strategy [STRATEGY]
> ```
>
> Wait for "WebSocket connected" message before starting coin terminals.
>
> ---
>
> **Terminal 2: BTC**
>
> ```bash
> cd /Users/ofers/Documents/trading-bot && python -m bot.ui.cli --coin BTC
> ```
>
> ---
>
> **Terminal 3: ETH**
>
> ```bash
> cd /Users/ofers/Documents/trading-bot && python -m bot.ui.cli --coin ETH
> ```
>
> ---
>
> **Terminal 4: SOL**
>
> ```bash
> cd /Users/ofers/Documents/trading-bot && python -m bot.ui.cli --coin SOL
> ```
>
> ---
>
> **Tip:** Arrange the 3 coin terminals side-by-side on your screen for a full market view.

Replace `[STRATEGY]` with the user's selected strategy.

---

## Step 3: Offer Quick Actions

Use the AskQuestion tool:

```
AskQuestion:
  title: "Quick Actions"
  questions:
    - id: "action"
      prompt: "What would you like to do?"
      options:
        - id: "copy_server"
          label: "Copy data server command"
        - id: "copy_all"
          label: "Show all commands again"
        - id: "done"
          label: "I'm done"
```

If "copy_server": Output just the data server command in a code block for easy copying.

If "copy_all": Re-display all 4 commands.

If "done": End the command.

---

## Notes

- The data server must be running before starting coin terminals
- Each coin terminal polls its state file from `data/live-state/`
- Press `q` in any terminal to quit that panel
- Press `Ctrl+C` in the data server terminal to stop everything
