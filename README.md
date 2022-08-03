# MDE to iCal - Export MyDisneyExperience Plans to iCalendar format
This is a fairly hacky (read: probably going to be broken) Python script to process the JSON planner from MyDisneyExperience and convert into an iCalendar format to be imported into your chosen calendar application of choice.


## How to use
You will need to obtain your JSON plans file from MyDisneyExperience. The easiest way is to grab this from your web browser 'Inspector' tool - I've based the below on the Firefox browser, but other modern browsers should be essentially the same:

  1. Visit the [MDE Planning page](https://www.disneyworld.co.uk/plan/) - note the URL may be different if you're outside of the UK
  2. Right Click -> 'Inspect' (at least in Firefox, other browsers have similar functionality, e.g. Developer Tools in Chrome)
  3. Select the 'Network' tab, and reload the page
  4. Find the request for the "file" named (at the time of writing) `daily?status=active`, then view the 'Response' to this request. Make sure you select the 'Raw' checkbox
  5. Select All and Copy this JSON (all the text starting with, and containing lots of `{` characters), and save it somewhere
  6. Create a file and paste this JSON blob into it, and save it somewhere
  7. Run `mde2ical.py <filename>`, where `<filename>` is the name of the file you created above
  8. A VCS (iCalendar/VCalendar) file will be created and the name printed on screen
  9. Load this into your calendar app of choice!

## Automatically obtaining your plans
There is a simple-ish script in `getJson.py` that uses [Selenium Wire](https://pypi.org/project/selenium-wire/) to automatically perform the MDE login and download your plans JSON. Due to the nature of how automatic web scraping works, this may break at any time.

Its hard-coded to use the Chrome webdriver (so make sure you have this installed!) and will output your plans to `my_plans.json`.

This does simplify the how to use section a bit:

  1. Run `getJson.py`
  2. Run `mde2ical.py my_plans.json`
  3. Load `my_plans.vcs` into your calendar!
  
  
## TODO
  - [X] Automatically login to MDE and grab the JSON, removing the horrid stuff above (see https://github.com/cwendt94/espn-api/discussions/150 for some details, the tl;dr is that Disney now use Google reCaptcha so we can't just programatically scrape the API)
  - [ ] Support additonal event types - currently I don't have any Genie+/$ILL reservations so I don't know how these look
  - [ ] Process additional 'Ticketed Events' (such as MNSSHP) and add these to the calendar

## Your code is rubbish / this doesn't work / Why don't you support $event_type?
Pull requests are welcome :)

### Disclaimer
This program is in no way affiliated or endorsed by Disney, or any of their subsidiaries or affiliates.
