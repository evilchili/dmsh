from pathlib import Path

from prompt_toolkit.application import get_app
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.key_binding import KeyBindings
from rolltable.types import RollTable

from dmsh.shell.base import BasePrompt, command
from dmsh import campaign
from dmsh import jobs
from dmsh import striders
from dmsh import hoppers
from dmsh import croaker

from reckoning.calendar import TelisaranCalendar
from reckoning.telisaran import Day
from reckoning.telisaran import ReckoningError

import npc

BINDINGS = KeyBindings()

ANCESTRY_PACK, ANCESTRIES = npc.load_ancestry_pack()
ANCESTRIES['strider'] = striders
ANCESTRIES['hopper'] = hoppers


class DMShell(BasePrompt):
    def __init__(self, cache={}):
        super().__init__(cache)
        self._name = "DM Shell"
        self._prompt = ["dm"]
        self._toolbar = [("class:bold", " DMSH ")]

        self._croaker = croaker.CroakerClient(
            host=self.cache['croaker_host'],
            port=self.cache['croaker_port']
        )

        self._key_bindings = BINDINGS
        self._register_subshells()
        self._register_keybindings()

        self._data_path = Path(self.cache['data_path']).expanduser() / Path(self.cache['campaign_name'])

        self.cache['campaign'] = campaign.load(
            path=self._data_path / Path("saves"),
            name=self.cache['campaign_name'],
            start_date=self.cache['campaign_start_date'],
            console=self.console
        )
        self._campaign = self.cache['campaign']

    def _register_keybindings(self):
        self._toolbar.extend(
            [
                ("", " [?] Help "),
                ("", " [F2] Wild Magic Table "),
                ("", " [F3] Trinkets"),
                ("", " [F4] NPC"),
                ("", " [F5] Date"),
                ("", " [F6] Job"),
                ("", " [F8] Save"),
                ("", " [F9] Music Hotkeys"),
                ("", " [^1-9] Music"),
                ("", " [^Q] Quit "),
            ]
        )

        @self.key_bindings.add("m", "1")
        def music_session_start(event):
            self.music(["play", "session_start"])

        @self.key_bindings.add("m", "2")
        def music_session_start(event):
            self.music(["play", "sahwat"])

        @self.key_bindings.add("m", "3")
        def music_session_start(event):
            self.music(["play", "battle"])

        @self.key_bindings.add("m", "4")
        def music_session_start(event):
            self.music(["play", "boss"])

        @self.key_bindings.add("m", "5")
        def music_session_start(event):
            self.music(["play", "tense"])

        @self.key_bindings.add("m", "6")
        def music_session_start(event):
            self.music(["play", "quiet"])

        @self.key_bindings.add("m", "7")
        def music_session_start(event):
            self.music(["play", "adventure"])

        @self.key_bindings.add("m", "8")
        def music_session_start(event):
            self.music(["play", "mystery"])

        @self.key_bindings.add("m", "9")
        def music_session_start(event):
            self.music(["play", "ffxii_battle"])

        @self.key_bindings.add("c-q")
        @self.key_bindings.add("c-d")
        @self.key_bindings.add("<sigint>")
        def quit(event):
            self.quit()

        @self.key_bindings.add("?")
        def help(event):
            self.help()

        @self.key_bindings.add("f2")
        def wmt(event):
            self.wmt()

        @self.key_bindings.add("f3")
        def trinkets(event):
            self.trinkets()

        @self.key_bindings.add("f4")
        def npc(event):
            self.npc()

        @self.key_bindings.add("f5")
        def date(event):
            self.date()

        @self.key_bindings.add("f6")
        def job(event):
            self.job()

        @self.key_bindings.add("f8")
        def save(event):
            self.save()

        @self.key_bindings.add("f9")
        def music(event):
            self._music_hotkeys()


    def _music_hotkeys(self):
        self.console.print("To switch music streams, press [b]m[/b] followed a number 1-9:")
        self.console.print("  [b]1[/b]  Session Start")
        self.console.print("  [b]2[/b]  Sahwat Overland")
        self.console.print("  [b]3[/b]  Overland Battle")
        self.console.print("  [b]4[/b]  Boss Battle")
        self.console.print("  [b]5[/b]  Tense")
        self.console.print("  [b]6[/b]  Quiet")
        self.console.print("  [b]7[/b]  Dungeon Adventure")
        self.console.print("  [b]8[/b]  Dungeon Mystery")
        self.console.print("  [b]9[/b]  Dungeon Battle")
        self.console.print("\nSee also the [link]music[/link] command.")

    def _handler_date_season(self, *args):
        self.console.print(self.cache['calendar'].season)

    def _handler_date_year(self, *args):
        self.console.print(self.cache['calendar'].calendar)

    def _handler_date_inc(self, days):
        offset = int(days or 1) * Day.length_in_seconds
        self._campaign['date'] = self._campaign['date'] + offset
        return self.date()

    def _handler_date_dec(self, days):
        offset = int(days or 1) * Day.length_in_seconds
        self._campaign['date'] = self._campaign['date'] - offset
        return self.date()

    def _handler_date_set(self, new_date):
        try:
            self._campaign['date'] = campaign.string_to_date(new_date)
        except ReckoningError as e:
            self.console.error(str(e))
            self.console.error("Invalid date. Use numeric formats; see 'help date' for more.")
        self.cache['calendar'] = TelisaranCalendar(today=self._campaign['date'])
        return self.date()

    def _rolltable(self, source, frequency='default', die=20):
        source_file = self._data_path / Path("sources") / Path(source)
        return RollTable(
            [source_file.read_text()],
            frequency=frequency,
            die=die
        ).as_table()

    @command(usage="""
    [title]DATE[/title]

    Work with the Telisaran calendar, including the current campaign date.

    [title]USAGE[/title]

        [link]> date [COMMAND[, ARGS]][/link]

        COMMAND     Description

        season      Print the spans of the current season, highlighting today
        year        Print the full year's calendar, highlighting today.
        inc N       Increment the current date by N days; defaults to 1.
        dec N       Decrement the current date by N days; defaults to 1.
        set DATE    Set the current date to DATE, in numeric format, such as
                    [link]2.1125.1.45[/link].
    """, completer=WordCompleter(
        [
            'season',
            'year',
            'inc',
            'dec',
            'set',
        ]
    ))
    def date(self, parts=[]):
        """
        Date and calendaring tools.
        """

        if not self.cache['calendar']:
            self.cache['calendar'] = TelisaranCalendar(today=self._campaign['date'])

        if not parts:
            self.console.print(f"Today is {self._campaign['date'].short} ({self._campaign['date'].numeric})")
            return

        cmd = parts[0]
        try:
            val = parts[1]
        except IndexError:
            val = None

        handler = getattr(self, f"_handler_date_{cmd}", None)
        if not handler:
            self.console.error(f"Unsupported command: {cmd}. Try 'help date'.")
            return

        return handler(val)

    @command(usage="""
    [title]Save[/title]

    Save the campaign state.

    [title]USAGE[/title]

        [link]> save[/link]
    """)
    def save(self, parts=[]):
        """
        Save the campaign state.
        """
        path, count = campaign.save(
            self.cache['campaign'],
            path=self._data_path / Path("saves"),
            name=self.cache['campaign_name']
        )
        self.console.print(f"Saved {path}; {count} backups exist.")

    @command(usage="""
    [title]NPC[/title]

    Generate a randomized NPC commoner.

    [title]USAGE[/title]

        [link]> npc \\[ANCESTRY\\][/link]

    [title]CLI[/title]

        [link]npc --ancestry ANCESTRY[/link]
    """, completer=WordCompleter(list(ANCESTRIES.keys())))
    def npc(self, parts=[]):
        """
        Generate an NPC commoner
        """
        char = npc.random_npc([ANCESTRIES[parts[0]]] if parts else list(ANCESTRIES.values()))
        self.console.print(char.description + "\n")
        if char.personality:
            self.console.print(f"Personality: {char.personality}\n")
        if char.flaw:
            self.console.print(f"Flaw:        {char.flaw}\n")
        if char.goal:
            self.console.print(f"Goal:        {char.goal}\n")

    @command(usage="""
    [title]QUIT[/title]

    The [b]quit[/b] command exits dmsh.

    [title]USAGE[/title]

        [link]> quit|^D|<ENTER>[/link]
    """)
    def quit(self, *parts):
        """
        Quit dmsh.
        """
        self.save()
        try:
            get_app().exit()
        finally:
            raise SystemExit("")

    @command(usage="""
    [title]HELP FOR THE HELP LORD[/title]

    The [b]help[/b] command will print usage information for whatever you're currently
    doing. You can also ask for help on any command currently available.

    [title]USAGE[/title]

        [link]> help [COMMAND][/link]
    """)
    def help(self, parts=[]):
        """
        Display the help message.
        """
        super().help(parts)
        return True

    @command(
        usage="""
    [title]LOCATION[/title]

    [b]loc[/b] sets the party's location to the specified region of the Sahwat Desert.

    [title]USAGE[/title]

        [link]loc LOCATION[/link]
    """,
        completer=WordCompleter(
            [
                "The Blooming Wastes",
                "Dust River Canyon",
                "Gopher Gulch",
                "Calamity Ridge"
            ]
        ),
    )
    def loc(self, parts=[]):
        """
        Move the party to a new region of the Sahwat Desert.
        """
        if parts:
            self.cache["location"] = " ".join(parts)
        self.console.print(f"The party is in {self.cache['location']}.")

    @command(usage="""
    [title]OVERLAND TRAVEL[/title]

    [b]ot[/b]

    [title]USAGE[/title]

        [link]ot in[/link]
    """)
    def ot(self, parts=[]):
        """
        Increment the date by one day and record
        """
        raise NotImplementedError()

    @command(usage="""
    [title]WILD MAGIC TABLE[/title]

    [b]wmt[/b] Generates a d20 wild magic surge roll table. The table will be cached for the cache.

    [title]USAGE[/title]

        [link]> wmt[/link]

    [title]CLI[/title]

        [link]roll-table \\
                sources/sahwat_magic_table.yaml \\
                --frequency default --die 20[/link]
    """)
    def wmt(self, parts=[], source="sahwat_magic_table.yaml"):
        """
        Generate a Wild Magic Table for resolving spell effects.
        """
        if "wmt" not in self.cache:
            self.cache['wmt'] = self._rolltable(source)
        self.console.print(self.cache['wmt'])

    @command(usage="""
    [title]TRINKET TABLE[/title]

    [b]trinkets[/b] Generates a d20 random trinket table.

    [title]USAGE[/title]

        [link]> trinkets[/link]

    [title]CLI[/title]

        [link]roll-table \\
                sources/trinkets.yaml \\
                --frequency default --die 20[/link]
    """)
    def trinkets(self, parts=[], source="trinkets.yaml"):
        """
        Generate a trinkets roll table.
        """
        self.console.print(self._rolltable(source))

    @command(usage="""
    [title]LEVEL[/title]

    Get or set the current campaign's level. Used for generating loot tables.

    [title]USAGE[/title]

        [link]> level [LEVEL][/link]

    """)
    def level(self, parts=[]):
        """
        Get or set the current level of the party.
        """
        if parts:
            newlevel = int(parts[0])
            if newlevel > 20 or newlevel < 1:
                self.console.error(f"Invalid level: {newlevel}. Levels must be between 1 and 20.")
            self._campaign['level'] = newlevel
        self.console.print(f"Party is currently at level {self._campaign['level']}.")

    @command(usage="""
    [title]JOB[/title]

    Generate a random job.

    [title]USAGE[/title]

        [link]> job[/link]

    """)
    def job(self, parts=[]):
        """
        Generate a random jobs table.
        """
        source_path = self._data_path / Path("sources")
        self.console.print(jobs.generate_job(source_path))

    @command(usage="""
    [title]PLACE[/title]
    """)
    def place(self, parts=[]):
        """
        Select random place names.
        """
        freq = parts[0] if parts else 'nodesert'
        self.console.print(self._rolltable("locations.yaml", frequency=freq, die=4))

    @command(usage="""
    [title]MUSIC[/title]

    [b]music[/b] Croaker controller.

    [title]USAGE[/title]

        [link]> music [COMMAND[, ARGS]][/link]

        COMMAND      Description

        list [NAME]  List available playlists, or the contents of the NAME playlist
        play NAME    Switch to the named playlist
        skip         Skip the current track
    """, completer=WordCompleter([
        'list',
        'play',
        'skip',
    ]))
    def music(self, parts=[]):
        """
        Control the music player
        """
        if parts:
            cmd, *args = parts
        else:
            cmd = 'list'
            args = []

        handler = getattr(self._croaker, cmd, None)
        if not handler:
            self.console.error(f"Unsupported command: {cmd}. Try 'help music'.")
            return
        self.console.print(handler(*args))
