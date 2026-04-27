# TODO: create script which will build HTML based on markdown file (data/collection.md) and template.html.
# These things should be get from md file:
# - Title
# - Masthead: Tagline and Chain
# - Preface: Headline and Body
# - Records
# - Colophon
# Images for records should be downloaded to folder images, and samed with discogs release id followed by extension.
# Template has the next fields and considerations:
# 
# <!--example--> ... <!--/example--> - should be removed.
# <!--template_timeline--> ... <!--/template_timeline--> - should be copied and used as template, but removed too.
# <!--template_record--> ... <!--/template_record--> - should be copied and used as template, but removed too.
# <!--sparked_event--> ... <!--/sparked_event--> and <!--sparked_target--> ... <!--/sparked_target--> should be copied and used as template, but removed too. There can be either one sparked_event or one sparked_target in one record. For event we need just test in appropriate fild, but for target we need record number.
# <!--led_to--> ... <!--/led_to--> - should be copied and used as template, but removed too. There can be several led_to entries.
# 
# Format with leading 0 depends on what number of records we have, like if we have 50 records, 1 will become 01, and 10 will be 10. If we have 100 records, 1 will become 001, and 10 will be 010.
# 
# - {{TITLE}}
# - timeline items:
#   - {{YEAR_START_CLASS}} - "is-year-start" or ""
#   - {{NUM}} - record number in a format with leading 0
#   - {{MONTH_YEAR}}
#   - {{YEAR}}
#   - {{MON}}
# - {{ISSUE_NO}} - last record number in a format with leading 0
# - {{TAGLINE}}
# - {{CHAIN}}
# - {{HEADLINE}} - md "*" should be replaced with "<em>" tag
# - {{BODY}} - text should be split by "\n" and every part put in "<p>" tag
# - {{SIGNOFF}}
# - {{RC}} - records count (without leading 0)
# - {{OT}} - length of the collecting period in the next format: words are wrapped in spans, while numbers are as is: "3<span> years</span> 5<span> months</span>". If there is just round year then: "3<span> years</span>". Last date during calculations should be considered as current month and year
# - {{FROM_TO}} - months with years should be formatted like this "from August 2024 to December 2027". Last date during calculations should be considered as current month and year
# - {{CC}} - countries count
# - {{COUNTRIES}} - countries list, like "Poland, Germany, Czech Republic, USA, Denmark, Romania, Spain"
# - {{MC_ARTIST}} - most collected artist, like "David Bowie"
# - {{MC_ARTIST_RC}} - most collected artist records count (without_leading 0)
# - records items:
#   - {{SIDE}} - should be "A" from odd items, and "B" for even
#   - {{COVER_URL}} - url of cover which we've downloaded and put to the folder "images"
#   - {{COVER_ALT_TEXT}} - alt text such as "Cover of Linkin Park — Papercuts"
#   - {{DISCOGS_URL}} - url to particular release, can be easily resolved by release id, like: https://www.discogs.com/release/30348920.
#   - {{RN}} - record number in a format with leading 0
#   - {{DATE_ADDED}} - date in the next format: "06 AUG 2024"
#   - {{FROM}} - where it comes from in the next format: "Internet, Poland"
#   - {{CAT_NO}} - catalog number in format with leading 0/how many records, like: "01/39"
#   - {{ARTIST}} - like "Linkin Park"
#   - {{ALBUM}} - like "Papercuts"
#   - {{SPARKED_EVENT}} - like "Previnyl"
#   - {{SPARKED_TARGET}} - like "№ 01 — Linkin Park"
#   - {{SPARKED_TARGET_NUM}} - record number in a format with leading 0
#   - {{NOTE}} - Things as quotes and others should be safely replaced for html like here: "It starts with Linkin Park. One of my favorite bands, ever since I first heard &quot;In The End.&quot; They&#x27;re the kind of band you fall for on the first song. Each new album from Minutes to Midnight always sounded like a new band — but the band you loved from the very first listen. Their experiments with different styles always felt awesome. And everything changes — the world changes, you change, the band and their music change — but you still love it. Isn&#x27;t that something? This compilation album was almost predefined as the first item in my collection."
#   - {{LED_TO_NUM}} - record number in a format with leading 0
#   - {{LED_TO_TARGET}} - like "№ 04 — Mike Shinoda"
# - {{COLOPHON}} - "\n" should be replaced with "<br>"
# - {{TOP_ARTISTS}} - Top 5 artists with their number of records, separated with "<br>", like "David Bowie — 3<br> Linkin Park — 6<br> Scorpions — 4<br> Marianne Faithfull — 2<br> Sanah — 2"
