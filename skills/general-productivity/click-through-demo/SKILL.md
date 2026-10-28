---
name: click-through-demo
display_name: Click-Through Demo
icon: assets/pointer.svg
description: "Turn a website into a self-contained click-through HTML demo captured from the user's own logged-in browser. It reads the site, proposes tours, and builds one file with a spotlight on each click, captions, chapters, zoom, blur, and embedded videos or images. Use when asked to 'make a click-through demo of this site', 'build an interactive product tour', 'record a guided walkthrough of this page', 'create an interactive demo from my browser', 'turn this site into a clickable demo', 'rebuild my demo after I edited demo.json', 'show me an example click-through demo', or 'ctd help'."
created_date: "2026-10-26"
last_updated: "2026-10-27"
tools: [load_skill, run_python, file_read, file_write, file_edit, file_copy, file_delete, folder_create, file_read_image, open_in_session_tab]
readme: "Read assets/README.md before running. Its ## Pre-requisites section lists the Amazon Quick Web Browser skill as a required local dependency. Confirm it is available and stop if it is missing."
preferred_model: smart
preferred_thinking: medium
inputs:
  - name: url
    description: "The page the demo starts on (http or https)"
    type: url
    required: true
  - name: goal
    description: "Optional: what the demo should show, as an outcome or a list of steps. When empty, the skill proposes tours."
    type: string
    required: false
    default: ""
  - name: output_folder
    description: "Folder to save the finished demo in. Chosen on the approval card from the folders the user actually has, which the skill lists first."
    type: path
    required: true
  - name: max_steps
    description: "Most screens one demo may have"
    type: number
    required: false
    default: 8
checksum: "sha256:4b7a6607b2cb9b47839ab3f2e4527bb08669f1886d1cedd21a733512c0751bac"
id: ae0d8dc5ca614079bb3c7aab5a14cb48
---

## Overview

The skill reads a website as text, proposes tours, and captures the one the user approves in their own browser. Each screen is captured after the page finishes loading, with the next click measured from the live page. The steps go into demo.json, and the skill builds one self-contained HTML demo from that file, so the demo can be edited and rebuilt later without new screenshots.

## Workflow

<Goal>
A finished run produces one index.html in {{output_folder}} that
- opens offline, with every screenshot embedded at the browser's full device resolution unless the user asked for a smaller file
- follows the approved tour from {{url}} in no more than {{max_steps}} screens
- spotlights the element the viewer clicks next on every screen except the last, measured from the live page and confirmed on the check image
- shows only fully loaded screens, never a spinner or an empty table
- has a short title and a plain-text caption on every screen that match what the screen shows
- was captured without any irreversible action on the site

The delivery message names any personal or account information in the screenshots and what was blurred. The user answers one approval card before capture and only real decisions after it.
</Goal>

<Definitions>
<Definition - Work folder>
`artifacts/<slug>/` in the session workspace, where `<slug>` is the tour name in lowercase words joined by hyphens, at most 40 characters. The folder holds demo.json, changes.json, snapshot.json, `screenshots/step-NN.png`, any `media/` files, index.html, and hotspot-check.png. The scripts run in the sandbox, so all work happens here before the finished files are copied to {{output_folder}}.
</Definition - Work folder>

<Definition - Trusted folder>
A folder on the user's computer that Amazon Quick can read and write. Listing the allowed folders with no path returns them.
</Definition - Trusted folder>

<Definition - Skill folder>
The base directory the skill was loaded from.
</Definition - Skill folder>

<Definition - Step>
One fully loaded screen plus the single action that leads to the next screen. The last step has no action.
</Definition - Step>

<Definition - Ready screen>
A screen that passed both checks in <Resource key="wait-for-ready">.
</Definition - Ready screen>

<Definition - Hotspot>
The rectangle around the element the viewer clicks next, in percentages of the viewport (`x`, `y`, `w`, and `h`, each from 0 to 100), with a `zoom` from 1 to 3. <Resource key="measure-hotspot"> describes how to measure it.
</Definition - Hotspot>

<Definition - Look-only action>
Opening a page, following a link, clicking a table row, switching a tab, applying a filter, opening a menu or dropdown, hovering, scrolling, or typing a search term.
</Definition - Look-only action>

<Definition - Irreversible action>
Any action that is not look-only. Submitting a form other than a search, sending, posting, publishing, saving, creating, deleting, buying, paying, inviting, starring, following, exporting, and changing a setting or permission all count.
</Definition - Irreversible action>
</Definitions>

<Rules>
1. Before opening any page, read `## Pre-requisites` in <Resource key="readme"> and confirm the browser is reachable.
2. Plan before capturing. Scout as text only, per <Resource key="scout-and-plan">, and get one tour approved before creating any file or taking any screenshot.
3. Ask only for decisions the user can make. Find or decide selectors, links, resolution, image format, file size, and wait times yourself. Every question puts the recommended option first, with defaults already chosen.
4. Perform only look-only actions. When the tour reaches an irreversible action, make that screen the last step with its control as the area of interest, leave the control unclicked, and tell the user where the demo stopped and why.
5. Never type passwords, one-time codes, or other secrets, and never sign in for the user. When a sign-in page appears, ask the user to sign in in their own browser and wait for them to confirm.
6. Open only http and https addresses. Leave browser-internal pages, such as settings, extension, and `about:` pages, alone.
7. Capture only a ready screen. Follow <Resource key="wait-for-ready"> after every navigation and every click. Never wait inside the page with an async loop, because background tabs slow its timers and the loop stalls.
8. Measure each hotspot from the live page, per <Resource key="measure-hotspot">, immediately before that step's screenshot and with no scrolling in between. Never estimate coordinates from an image.
9. Capture and build at the browser's full device resolution. Build a smaller copy only when the user asks for one. A change in viewport size or pixel ratio between steps usually means the browser window moved to another display, so stop and tell the user before capturing more.
10. Write titles, captions, and actions per <Resource key="viewer-design">.
11. Record each step in demo.json through scripts/run_demo_store.py as soon as it is captured, so an interrupted run can resume from the file. Make your own later changes through the script as well, and edit demo.json directly only to repair a hand edit the user asked you to fix. Users may edit demo.json themselves, and the rebuild names any mistake they make.
12. Never hardcode or guess where a demo goes. List the user's available folders on every run and offer each <Definition - Trusted folder> by name, with a trusted folder recommended first. Working files go only to the work folder, and the finished demo goes only to {{output_folder}}.
13. When the user chose blur, blur every personal-information match before building. Every delivery names the personal or account information the screenshots show and what was blurred.
14. Stop at {{max_steps}} screens. If the tour needs more, say so and offer to split it into two demos or raise the limit.
15. Open demos in the user's browser. The Amazon Quick side panel has no internet access, so https images and video links do not load there. Use a session tab only when the user asks for one or no browser is available, and say what will not load.
</Rules>

<Agent Annotations>
Workflow steps carry a prefix that says who acts and what happens next.
- [Agent] = Act with tools without involving the user.
- [Ask user] = Present to the user and wait for the response. When the step needs a decision, offer numbered options with the recommended one first and marked "(recommended)", and make the last option "Other", answered by typing its number and the user's own answer. Never leave a decision as an open question when a sensible default exists.
- [Decide] = Evaluate the conditions and follow the matching branch.
- [Think] = Reason internally, with no tools or output. Generate three or more candidate approaches, score them against <Goal> and <Rules>, pick the best and say why, then ask what could go wrong before continuing.
</Agent Annotations>

<Gotchas>
- Navigation often returns before a page's data arrives, with only the header and footer drawn. Waiting for an element that only the planned screen has (Rule 7) prevents empty screens.
- Some clickable elements, such as table rows that open a record, are not links. Click them, because there is no address to navigate to.
- Some sites render hidden copies of a link, so clicking a link by its element number can open a different page. For links, navigate to the address the hotspot measurement returns.
- JavaScript run inside a batch of browser actions does not return its value. Run each script as its own browser call.
- Running JavaScript in the page needs the user's permission. Every measurement fails while it is declined, so the pre-requisite check asks for it once, up front.
- Typing into the page needs its own permission. If it is declined, open the search results address directly instead, drop the typed-search screen from the tour, and say so in the delivery.
- Screenshots come out at device-pixel size, so the image is the viewport width times the device pixel ratio. That is the full resolution Rule 9 asks for.
- The browser saves a screenshot to the session's `artifacts/` folder under its save name. Copy it into the work folder's `screenshots/` before recording the step.
- To view an image in the session workspace, prefix its path with `workspace/`.
- The skill's scripts import by module name in run_python. The sandbox does not pass `sys.argv`, so call each script's `main([...])` with an argument list.
- A logged-in browser shows the user's avatar, account name, and controls only they can see, and all of it lands in the screenshots.
- The device's open-file tool refuses .html files. Give the user the demo's path and its `file://` address to open in their browser.
- Copying a whole folder to the user's computer fails, so copy files one at a time.
- Copying a file onto the user's computer leaves an existing file of the same name in place, even when the copy reports success. Delete the old file first.
</Gotchas>

<Instructions>

<Workflow - Router
description="Send ctd commands and requests to the right workflow."
tools=[]
triggers=["User asks for a click-through demo, product tour, or walkthrough of a site", "User asks to change a demo they built", "User asks to see an example demo or result", "ctd help", "ctd", "ctd build", "ctd edit", "ctd example"]
>

1. [Decide] What is the user asking for?
   Validate: exactly one path is chosen. If the request is ambiguous, ask which one they mean.
   If fails: show <Workflow - Help>.
   - `ctd help`, a bare `ctd`, or "what can this do" → <Workflow - Help>
   - `ctd build`, or a request to make a demo, tour, or walkthrough from a URL → <Workflow - Build Demo>
   - `ctd edit`, a request to change, add media to, blur, shorten, or shrink an existing demo, or "I edited demo.json, rebuild it" → <Workflow - Edit Demo>
   - `ctd example`, "show me an example", or "what does a result look like" → <Workflow - Show Example>
</Workflow - Router>

<Workflow - Help
description="Show the ctd command menu."
tools=[]
triggers=["ctd help", "ctd", "User asks what this skill can do"]
>

1. [Agent] Render <Resource key="help-menu">, then stop and wait for the user's choice.
   Validate: the menu lists `ctd help`, `ctd build`, `ctd edit`, and `ctd example`, each with one line.
   If fails: render it again from <Resource key="help-menu">.
</Workflow - Help>

<Workflow - Show Example
description="Show the bundled Amazon.com example demo and the prompt that built it, then offer to help build the user's own."
tools=[file_read, file_copy, folder_create, open_in_session_tab]
triggers=["ctd example", "User asks to see an example demo, a sample result, or what the output looks like"]
>

1. [Agent] Read <Resource key="example-amazon-search"> for the prompt and the plan it produced.
   Validate: the prompt and the plan are loaded.
   If fails: say the example file is missing from the skill and offer <Workflow - Build Demo> instead.

1. [Agent] List the user's available folders. If a <Definition - Trusted folder> exists, create a `ctd-example` folder in it, copy <Resource key="example-amazon-search-output"> there as `index.html`, and give the user its path and `file://` address to open in their browser, per Rule 15.
   Validate: the user has the example's path to open in their browser.
   If fails: with no trusted folder, copy it to `ctd-example/index.html` in the session's artifacts folder (create the folder first), open it in a session tab, and say that https images and video links will not load there.

1. [Ask user] In a few lines, show the prompt that built the example as a copyable block, then describe its screens and chapters, what was blurred and why, and where the tour stops. Offer 1. build a demo of my own site (recommended), 2. build this Amazon demo with my account, 3. show how a demo is edited, 4. Other.
   Validate: the user picks an option.
   If fails: summarize the example in one line and ask again.

1. [Decide] Which option did the user pick?
   Validate: one branch is chosen.
   If fails: stop and wait for the user.
   - Own site → <Workflow - Build Demo> with the URL they give.
   - This Amazon demo → <Workflow - Build Demo> with the example's prompt as {{url}} and {{goal}}.
   - How editing works → explain <Workflow - Edit Demo> using the change set in <Resource key="example-amazon-search">.
</Workflow - Show Example>

<Workflow - Build Demo
description="Scout a site, get one tour approved, capture it from the user's browser, and build the demo."
tools=[load_skill, file_read, folder_create, run_python, file_copy, file_write, file_delete, file_read_image, open_in_session_tab]
triggers=["ctd build", "User asks to make a click-through demo, product tour, or walkthrough of a site"]
>

1. [Agent] Check the pre-requisites per Rule 1. Load the Web Browser skill, list the user's open browser tabs, open {{url}}, and run the quick check from <Resource key="wait-for-ready">. Tell the user to choose Allow on the permission prompts for running page scripts and for typing into the page. The first check opens the page-script prompt, and the first typed search term opens the typing prompt.
   Validate: the browser tools load, the tab list comes back, and the quick check returns a result.
   If fails: stop. If only the page-script permission was declined, explain that measuring needs it and ask whether to retry. Otherwise tell the user the skill needs the Amazon Quick desktop app open and awake with a browser chosen in its settings, and link <Resource key="connections-desktop">.

1. [Decide] Is {{url}} known, and does it start with `http://` or `https://`?
   Validate: one branch is chosen.
   If fails: ask for the URL only.
   - Yes → continue.
   - No → ask which page to start from, with the user's open tabs as numbered options and Other last.

1. [Agent] Scout per <Resource key="scout-and-plan">. Open {{url}}, wait for it to be ready, read it as text, and follow the most promising links within the scouting budget.
   Validate: the budget was kept, no screenshot was taken, and the pages read list links or controls to plan from.
   If fails: follow Rule 5 if a page needs sign-in. If a page stays empty, ask whether to wait longer or start from another page.

1. [Think] Plan 2 or 3 tours from the scouting results, per the planning section of <Resource key="scout-and-plan">. For a store, a search-driven site, or a signed-in site, follow the shape of <Resource key="example-amazon-search">. If {{goal}} is set, make it the first tour. Check every action against Rule 4 and every tour's length against Rule 14.
   Validate: each tour follows the planning rules, names its screens in plain words, and has no irreversible action before its last screen.
   If fails: drop any tour that breaks a rule and plan another.

1. [Agent] List the user's available folders (a folder listing with no path) and keep each <Definition - Trusted folder> for the save question.
   Validate: the listing returned, even if it holds no folders on the user's computer.
   If fails: offer only the session's artifacts folder and say why.

1. [Ask user] Show the approval card from <Resource key="scout-and-plan">, using the folders from the previous step. Mention that zoom and blur can be changed later without recapturing.
   Validate: the user picked a tour and a save location. Extras may be empty.
   If fails: ask again for the unanswered question only.

1. [Agent] Create the work folder and its `screenshots/` subfolder per <Definition - Work folder>. If the folder already holds a demo.json with steps, run `show` and ask 1. resume after the last captured step (recommended), 2. start over in `<slug>-2`, 3. Other. To resume, open the last step's `url`, wait for it to be ready, measure its hotspot again to get the address or control, perform its action as in step 14, and continue from step 10.
   Validate: the folders exist, and the resume choice, if there was one, is made.
   If fails: use `<slug>-2` and report the error.

1. [Agent] Create the demo in demo.json by applying a change set with the demo title, start URL, goal, accent color, and chapters, plus the intro card, closing card, and call-to-action link when the user chose those extras, per <Resource key="demo-store">.
   Validate: the apply call returns 0.
   If fails: fix the field the error names and apply again.

1. [Agent] Open {{url}} in the user's browser unless it is already open on that page.
   Validate: the browser reports the page opened.
   If fails: retry once, then report the error.

1. [Agent] Wait for a ready screen per Rule 7.
   Validate: the screen is a <Definition - Ready screen>.
   If fails: follow the reading-the-result section of <Resource key="wait-for-ready">. When it says to ask, offer 1. wait again (recommended), 2. reload the page, 3. skip this screen and re-plan, 4. Other. When the check reports the tab as hidden, make the first option "I brought the browser window to the front, wait again", because some sites do not load content in a hidden tab.

1. [Agent] Measure this screen per <Resource key="measure-hotspot">. On the last screen, measure the area of interest instead of a click target. Take the screenshot straight away, saved as `step-NN` (two digits), and copy it to `screenshots/step-NN.png`. If blur is on, look at the screenshot for anything the measurement could not find, such as history-based rows or account-only controls, and add blur areas for them.
   Validate: the measurement found the planned element, and the screenshot shows the planned screen with nothing covering the hotspot.
   If fails: dismiss a cookie banner or popup with a look-only action, wait for a ready screen, and measure and capture once more. If the element is still missing, re-plan from the current screen (step 4).

1. [Agent] Record the step by applying a change set with its title, caption, and action (Rule 10), its `url`, `screenshot`, and `load_ms`, the hotspot and zoom (zoom only if the user kept it on), the blur areas, and the load event. Then report progress, such as "Captured 3 of 5".
   Validate: the apply call returns 0 and `show` lists the step.
   If fails: fix the field the error names and apply again.

1. [Decide] Is this the last planned screen, or has the demo reached {{max_steps}} screens?
   Validate: one branch is chosen.
   If fails: treat it as the last screen.
   - Yes → go to step 15.
   - No → go to step 14.

1. [Agent] Perform the action the measurement chose. Navigate to its address when it says to navigate, otherwise click the marked element. Go back to step 10 for the next screen, waiting for something only the new screen has.
   Validate: the next wait succeeds on the planned next screen.
   If fails: go back to the previous step's `url`, wait, and try once more. If it fails again, re-plan from the current screen (step 4).

1. [Agent] Build. Export the snapshot with scripts/run_demo_store.py, then run scripts/create_demo.py with <Resource key="demo-template"> from the <Definition - Skill folder> and the work folder as the output, per <Resource key="demo-store">.
   Validate: both calls return 0 and the build logs the step count and file size.
   If fails: fix what the error names, usually a missing hotspot or media path, with a change set, then build again.

1. [Agent] Open `hotspot-check.png` from the work folder with the `workspace/` prefix. Each magenta box should sit on the element its step's action names, and each blue box should cover what it hides.
   Validate: every box is in the right place and none is cut off at an edge.
   If fails: for each wrong step, open its `url`, repeat steps 10 to 12 for it, then repeat step 15.

1. [Agent] Deliver. Copy the files into {{output_folder}} one at a time (see <Gotchas>): index.html first, then demo.json, snapshot.json, the screenshots, and any media, so later edits work from that folder. When that folder is on the user's computer, a copy will not overwrite a file of the same name, so remove the previous run's index.html, demo.json, and snapshot.json before copying over them. Give the user the demo's path and `file://` address to open in their browser, per Rule 15.
   Validate: index.html exists in {{output_folder}} and the user has its path.
   If fails: leave the demo in the work folder, say where it is, and report the copy error.

1. [Ask user] Report the screen count, the file size, the slowest page and its load time, and a link to index.html. State the privacy findings per Rule 13, and where and why the demo stopped if Rule 4 or Rule 14 cut it short. When a step has a video link, say it needs an internet connection to play. Offer 1. done, keep it as is (recommended when nothing sensitive is unblurred), 2. add a video or image to a step, 3. edit text, chapters, or cards, 4. Other.
   Validate: the user picks an option.
   If fails: summarize the result in one line and ask again.
</Workflow - Build Demo>

<Workflow - Edit Demo
description="Change a demo's text, cards, chapters, media, blur, zoom, length, or size, or rebuild it after the user edited demo.json, without recapturing."
tools=[file_read, file_copy, file_write, file_edit, file_delete, run_python, file_read_image, open_in_session_tab]
triggers=["ctd edit", "User asks to change, add media to, blur, shorten, or shrink a demo they built", "User says they edited demo.json and asks for a rebuild"]
>

1. [Ask user] Which demo? Offer 1. the demo built most recently in this session (recommended), 2. a folder you name, 3. Other. Skip this question when the user already named the demo or its folder.
   Validate: the folder holds demo.json and a `screenshots/` folder.
   If fails: say what is missing. A folder with only index.html cannot be edited, so offer to rebuild it with `ctd build`.

1. [Agent] If the folder is outside the session workspace, copy it into a work folder. Always copy the demo folder's demo.json over the work folder's copy, so edits the user made by hand are picked up. Run `show` and list the steps as numbered lines.
   Validate: the list matches demo.json.
   If fails: if the error says demo.json is not a valid demo file, the user's hand edit has a mistake, so explain it as in the failure path of step 7. Otherwise report the error and stop.

1. [Ask user] What should change? Offer 1. titles, captions, or actions (recommended), 2. add a video or image to a step, 3. intro, closing card, or call-to-action link, 4. chapters, 5. blur an area or turn zoom on or off, 6. remove steps from the end, 7. a smaller file, 8. I edited demo.json myself, just rebuild it, 9. Other. Skip this question when the user already said they edited demo.json. Reordering steps or adding one in the middle breaks the click path, so offer to recapture from that step with <Workflow - Build Demo> instead.
   Validate: each requested edit names a step or the demo, or the user chose a rebuild.
   If fails: ask about the unclear edit only.

1. [Decide] Did the user edit demo.json themselves?
   Validate: one branch is chosen.
   If fails: ask whether they changed demo.json by hand.
   - Yes → go to step 7.
   - No → continue.

1. [Agent] Prepare any media. Copy image or video files into the work folder's `media/` folder, and check that video links are direct https .mp4 or .webm links, per <Resource key="demo-store">. For a blur area, open that step's screenshot and turn the area the user describes into viewport percentages.
   Validate: every media file exists in `media/` and every link uses https.
   If fails: ask for a supported link or file.

1. [Agent] Apply the edits as one change set, per <Resource key="demo-store"> and Rule 10.
   Validate: the apply call returns 0 and `show` reflects the edits.
   If fails: fix the field the error names and apply again.

1. [Agent] Rebuild, check, and deliver with steps 15 to 17 of <Workflow - Build Demo>, using the demo's own folder as {{output_folder}}. For a smaller file, build the smaller copy described in <Resource key="demo-store">. After a hand edit, the check image in step 16 also confirms any highlight or blur area the user moved.
   Validate: the rebuilt index.html exists in the demo's folder and the user has its path.
   If fails: when the error comes from a hand edit, explain it in plain words using the hand-edits section of <Resource key="demo-store">. Name the step, the field, the value the user typed, and what is allowed. Offer 1. fix it for me (recommended), 2. I'll fix it myself and ask you to rebuild, 3. Other. To fix it, change only the named field in demo.json, then rebuild. For any other error, follow the failure path of the step that failed.

1. [Ask user] Show what changed and offer 1. done (recommended), 2. more edits, 3. Other.
   Validate: the user picks an option.
   If fails: treat it as done.
</Workflow - Edit Demo>

</Instructions>

<Resources>
<Resource key="help-menu">assets/help-menu.md</Resource>
<Resource key="readme">assets/README.md</Resource>
<Resource key="demo-template">assets/demo-template.html</Resource>
<Resource key="scout-and-plan">references/scout-and-plan.md</Resource>
<Resource key="wait-for-ready">references/wait-for-ready.md</Resource>
<Resource key="measure-hotspot">references/measure-hotspot.md</Resource>
<Resource key="demo-store">references/demo-store.md</Resource>
<Resource key="viewer-design">references/viewer-design.md</Resource>
<Resource key="example-amazon-search">references/examples/amazon-search.md</Resource>
<Resource key="example-amazon-search-output">assets/examples/amazon-search/index.html</Resource>
<Resource key="connections-desktop">https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html</Resource>
</Resources>
