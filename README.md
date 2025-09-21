# TicTacToe — GUI • AI • LAN Multiplayer (with Discovery)

A Python TicTacToe with:
- 🎨 **GUI**
- 🤖 **AI opponent** (Easy/Medium/Hard)
- 🌐 **LAN multiplayer** (UDP discovery + PIN-gated)

---

## ✨ Features

- **Play modes**
  - **PvAI** — You (X) vs AI (O). Difficulty: *Easy*, *Medium*, *Hard*.
  - **PvP Local** — Two players on the same machine.
  - **LAN Multiplayer** — Host a match and others on your network can discover & join.

- **LAN discovery**
  - Server replies to UDP broadcasts (default **9998**).
  - Clients scan the LAN and show join buttons (host name is bolded).

- **Security / Access**
  - **PIN required** to join a hosted game.
  - Server binds to `0.0.0.0` to allow LAN clients; game port is picked from the first available **high ephemeral** port.

---

## 🗂️ Project Structure

```
tictactoe/
├── __init__.py
├── README.md
├── game.py
├── ai.py
├── server_net.py
├── discover.py
├── cli.py
├── client_net.py
├── gui.py
├── test.py
└── guiFolder/
    ├── init.py
    ├── app.py
    ├── config.py
    └── pages/
        ├── init.py
        ├── home_page.py
        ├── game_page.py
        └── network_page.py
```

---

## 🚀 Running the Game

### 1. Navigate to the project root
Make sure your terminal is in the **parent directory** of `tictactoe/`.  
For example, if your code is at:

```
C:\Users\user\Downloads\tictactoe\
```

then run:
```bash
cd C:\Users\user\Downloads\
```

---

### 2. Launch the GUI
```bash
python -m tictactoe.gui
```

---

### 3. Local Testing (same machine)

1. Open one terminal:
   ```bash
   python -m tictactoe.gui
   ```
   → Host a game (enter a name + PIN).

2. Open a second terminal:
   ```bash
   python -m tictactoe.gui
   ```
   → Join the hosted game (enter name + PIN).
