# Wifite2 Interactive TUI

Wifite2 now includes an optional Interactive Text User Interface (TUI) that provides real-time updates and a modern terminal experience.

## Features

### Scanner View
- **Live target updates** - See networks appear in real-time as they're discovered
- **Color-coded information** - Signal strength (green/yellow/red) and encryption types
- **Scan statistics** - Track targets by encryption type, client count, and elapsed time
- **No scrolling** - All information updates in place

### Selector View
- **Interactive selection** - Navigate and select targets with keyboard
- **Visual feedback** - See your selections highlighted
- **Keyboard shortcuts** - Quick selection with single keys
- **Scrolling support** - Handle large target lists efficiently

### Attack View
- **Real-time progress** - Watch attack progress with live updates
- **Attack-specific metrics** - See relevant stats for each attack type
  - WEP: IVs collected, crack attempts, replay status
  - WPA: Handshake status, clients, deauth packets
  - WPS: PIN attempts, pixie dust status, lockout detection
  - PMKID: Capture attempts and status
- **Scrollable logs** - Review detailed attack logs
- **Progress bars** - Visual progress indicators

## Usage

### Enable TUI Mode

```bash
# Auto-detect (uses TUI if terminal supports it)
sudo wifite

# Force TUI mode
sudo wifite --tui

# Force classic text mode
sudo wifite --no-tui
```

### Keyboard Shortcuts

#### Scanner View
- `Ctrl+C` - Stop scanning and select targets
- `?` - Show help

#### Selector View
- `↑/↓` - Navigate up/down (Note: May be unreliable, use alternatives)
- `Space` - Toggle target selection
- `Enter` - Confirm selection and start attack
- `a` - Select all targets
- `n` - Deselect all targets
- `q` - Quit
- `?` - Show help

#### Attack View
- `Ctrl+C` - Skip current target
- `?` - Show help

## Requirements

- Python 3.6+
- `rich` library (automatically installed with wifite2)
- Terminal with minimum size: 80x24
- Color support (optional but recommended)

## Configuration

TUI settings can be configured in `wifite/config.py`:

```python
use_tui = None  # None=auto, True=force TUI, False=force classic
tui_refresh_rate = 0.5  # Seconds between updates
tui_log_buffer_size = 1000  # Max log entries
tui_debug = False  # Enable debug logging
```

## Troubleshooting

### TUI Won't Start

**Problem:** TUI mode requested but falls back to classic mode

**Solutions:**
- Check terminal size: `echo $COLUMNS x $LINES` (minimum 80x24)
- Verify rich library: `python3 -c "import rich; print(rich.__version__)"`
- Check TERM variable: `echo $TERM` (should not be 'dumb')
- Try forcing TUI: `sudo wifite --tui`

### Terminal Too Small

**Problem:** Error about terminal size

**Solution:** Resize your terminal window to at least 80 columns by 24 rows

### Arrow Keys Not Working

**Known Issue:** Arrow key navigation in selector may be unreliable

**Workarounds:**
- Use `a` to select all targets
- Use `n` to deselect all
- Use `Space` to toggle individual targets
- Use classic mode: `sudo wifite --no-tui`

### Display Issues

**Problem:** Garbled or incorrect display

**Solutions:**
- Clear terminal: `reset`
- Check for conflicting processes
- Try classic mode: `sudo wifite --no-tui`
- Update rich library: `pip3 install --upgrade rich`

## Debug Mode

Enable TUI debug logging to troubleshoot issues:

```bash
# Set debug flag in config or via environment
sudo wifite --tui

# Check logs
tail -f /tmp/wifite_tui.log
```

Debug logs include:
- TUI initialization events
- Key press events
- Rendering performance metrics
- Error messages and exceptions

## Fallback Behavior

The TUI automatically falls back to classic mode if:
- Terminal doesn't support required features
- Terminal size is too small
- Rich library is not available
- TUI initialization fails
- User specifies `--no-tui`

## Performance

The TUI is optimized for performance:
- Update throttling (50ms minimum between updates)
- Memory cleanup (limits log buffer to 1000 entries)
- Efficient rendering (only updates changed content)
- Minimal CPU usage during idle periods

## Known Limitations

1. **Arrow key navigation** - May require holding keys or multiple presses
2. **SSH sessions** - May have reduced functionality over SSH
3. **Screen/tmux** - Some features may not work in multiplexers
4. **Minimum terminal size** - Requires 80x24 minimum

## Classic Mode

Classic mode remains fully supported and is the default for:
- Terminals that don't support TUI
- Piped output or non-interactive sessions
- User preference (`--no-tui`)

All features work identically in both modes, only the presentation differs.

## Contributing

To improve the TUI:
1. Report issues with terminal type, size, and error messages
2. Test on different terminal emulators
3. Suggest UI improvements
4. Submit pull requests

## Credits

- TUI implementation uses the [rich](https://github.com/Textualize/rich) library
- Original wifite2 by derv82
- Maintained by kimocoder
