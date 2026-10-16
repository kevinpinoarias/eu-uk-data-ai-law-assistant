# Accessibility checklist: a ten-minute screen-reader pass

## What a screen reader is

A **screen reader** is software that reads a web page aloud (or sends it to a braille display) for people who are
blind or have low vision. It does not read the picture of the page. It reads the page's *structure*: headings,
buttons, form fields, links, lists and the text of each, in order. You move around with the keyboard
(Tab, arrow keys, heading shortcuts), not the mouse.

That is why a page can look perfect and be unusable: a button drawn as a styled box with no label is
announced as just "button"; a result that appears after you press Ask is silent unless the page marks it as a
live area.

## What the automated tests already prove, and what they cannot

| Already checked by tests (`tests/test_web_page.py`, `tests/test_privacy_page.py`) | Only a person listening can judge |
|---|---|
| Text and background colours reach the WCAG AA contrast of 4.5:1, light and dark | Whether the spoken order makes sense |
| The page and each language section declare their language | Whether the Spanish is *pronounced* as Spanish |
| The text box has a label, a description and a length limit | Whether the labels are understandable out loud, not only present |
| A "skip to content" link exists and has a target | Whether the result is announced at a useful moment |
| The result area is announced; errors are alerts | Whether it is irritating (announced twice, too long) |
| The language buttons say which one is selected | Whether it feels natural to use for several minutes |

So the tests prove the *parts* are there. This pass checks whether the whole *sounds* sensible. It is not a
substitute for testing with people who use a screen reader every day, and the project does not claim it is.

## Which software

- **Windows (your machine):** NVDA, free and open source (nvaccess.org). Start it with Ctrl+Alt+N; stop it
  with Insert+Q. Silence it at any moment by pressing Ctrl.
- **Mac / iPhone:** VoiceOver is built in (Cmd+F5 on a Mac; triple-click the side button on an iPhone after
  enabling it in Settings).
- **Android:** TalkBack, built in.

Installing NVDA is a download: say the word and the filename, source and size are confirmed with you first.

## The pass (run the server in demo mode: `python -m law_assistant.serve --demo`)

Open `http://127.0.0.1:8000`, start the screen reader, and **close your eyes or turn the screen off**. Use only
the keyboard.

1. **First impression.** Reload the page. Does it announce the title and language? Is the first thing you hear
   useful, or a wall of notices?
2. **Skip link.** Press Tab once. You should hear "Skip to the question box". Press Enter. Focus should move
   to the question box.
3. **Question box.** Tab to it. You should hear its label, that it is an edit box, and its hint. Type
   `What is the highest fine under the GDPR?`
4. **Ask.** Tab to the Ask button, press Enter. You should hear a "searching" message, then the answer, without
   having to hunt for it.
5. **Reading the answer.** Press the screen reader's "next heading" key (H in NVDA). Do you reach "Result" (a heading that
   is invisible on screen but read aloud) and "Sources"? Are the sources readable as a list?
6. **A refusal.** Ask `Is this legal in California?` The refusal should be announced as clearly as an answer.
7. **An error.** Stop the server, press Ask. The network error should be announced at once (as an alert).
8. **Language switch.** Tab to the Español button, press Enter. Is the change announced? Does the page now read
   in Spanish with a Spanish voice? Ask `¿Cuál es la multa máxima?`
9. **Footer and privacy notice.** Tab to the "Privacy notice" link and open it. Are the two language sections
   announced as English and Spanish? Can you jump between headings?
10. **Zoom and phone width.** (No screen reader needed.) Zoom the browser to 200 % and then narrow the window to
    phone width. Nothing should be cut off, and you should never scroll sideways.

## Recording the result

Add a short entry to `docs/EXPERIMENTS.md` or `docs/JOURNEY.md`:

- date, software and version, browser;
- for each of the ten steps: *fine*, *awkward* (say how) or *broken*;
- what was changed in response, and a test for it where a test is possible.

Anything marked *awkward* or *broken* becomes a fix on the page, with the cause explained in the commit.

## What is honestly still unverified

No one has yet used the page with a screen reader. Until this pass is done, the claim the project may make is
"built to WCAG AA contrast and labelling rules and checked by automated tests", not "accessible to screen-reader
users".
