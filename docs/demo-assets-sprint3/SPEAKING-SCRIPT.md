# Speaking script — final review

Read it. That is fine. Look up at the end of each slide, not during.

One sentence per line. Pause where the line breaks.
**Bold** = slow down. Do not rush these.

---

## 1. Project A

This is Project A.
Not one sprint, the whole thing.
Everything you will see is from real runs on my own machine, most of it this morning.

---

## 2. It worked. I just couldn't tell you what was running.

On day one this was a small app and a README.
To put a change live, I built it on my laptop, copied it over, stopped the old container and started a new one.

It worked.
But if you asked me an hour later what was actually running, I could not tell you.
Everything after this slide is my answer to that.

---

## 3. Three sprints, one arc

Three sprints, one job each.
First, make the thing worth shipping.
Second, ship it without me.
Third, see what it is doing after.

---

## 4. From four commands to one merge

Putting a change live.
Before, that was me.
Four commands, in the right order, from memory.
It worked because I was paying attention.

Now I merge.
That is the whole thing.
The rest happens without me, the same way every time.

---

## 5. How fast can it tell me I'm wrong?

The question I built this around is not what does it check.
It is how fast can it tell me I am wrong.

So they run cheapest first.
Style takes seconds, a build takes minutes.
If my mistake is a cheap one, I want to know in seconds.

The fastest no I have had is eleven seconds.
That was the password check, and I will show you that one later.

---

## 6. One commit, all the way through

One commit, all the way through.
Under two minutes, eleven checks, green from my laptop to a running container.

---

## 7. Two machines. Both say latest. Same image?

Here is something I could not answer on day one.
My laptop had an image called latest.
The server had an image called latest.
Were they the same image?
I had no way to know.

Because latest is not a fact.
It is a name someone can move.
Two machines can both say latest and mean different things.

So now nothing is called latest.
Every image is named after the commit it came from, and that name can never move.

---

## 8. Now I can answer it in one command

And now it takes one command.
I ask the container which commit it is, I ask git which commit I pushed, and they match.

---

## 9. I tested one thing and shipped another.

Remember my promise at the start, that what runs is what passed the tests?
For a while that was not true, and I did not find it by being clever.

The image was shipping one version of the web server.
My tests were running on a different one.
Every test was green, on software nobody was actually using.

What found it was making the pipeline list every piece of software inside the image, and compare.
Six hundred and twenty one of them.
I would never have seen it by reading.

---

## 10. The safest undo is the one I use every day

When it goes wrong.
Before, I rebuilt the old version and hoped I picked the right one, while the broken one stayed up.

Now, undoing is the same deploy with an older commit.
There is no separate undo script on purpose.
One path, used every day, so it still works on the day I need it.

---

## 11. Three runs, eleven days — and the number moved once

A rollback plan nobody has run is just a paragraph.
So mine is a script.
It breaks the app on purpose, deploys the broken one, lets the checks catch it, undoes it, and times it.

I have run it three times over eleven days.
All three logs are in the repo.
The first two gave exactly the same numbers, twenty seven seconds to notice and seven to fix.
This morning it was twenty nine and eight.

So it repeats, but to within a few seconds, not exactly.
I would rather tell you that than round all three to one nice number.

---

## 12. Nobody should be looking for a hash at 2am

This is the deploy failing.
The checks refused it, so the deploy failed.
That is the right outcome, not a bug.

And this is the part I care about.
It printed the command to undo it, with the old commit already in it.
In a real incident nobody should be digging through history for a hash.

---

## 13. 37 seconds down, not 8

Here is the number I could have made look nicer, and did not.
Eight seconds to recover.
Thirty seven seconds actually down.

My deploy swaps the container before it checks it.
So the broken one served errors for the whole twenty nine seconds the checks spent retrying.
The checks limit the damage.
They do not stop it.

The real fix is checking the new one before it takes traffic.
I know how; it did not fit in the time.
And I did not lower the retry count to make the number look better.

One more thing.
Back then I only knew this happened because I was watching the screen.
In a few minutes I will show you the part that means I get told instead.

---

## 14. A green deploy tells you it started

Now the part I did not have at all until three weeks ago.
Before, once the container started, I was blind.
I found out something was wrong by trying the app myself.

Now the app reports its own numbers and writes logs a machine can read.
Three tools collect them.
And it is all set up in code, so I can delete the whole thing and get it back the same.

---

## 15. Numbers on top, words underneath

Two paths that meet in one place.

On top, numbers.
Prometheus pulls from the app, the containers and the machine, every fifteen seconds.

Underneath, text.
The app prints JSON, Alloy picks it up off Docker, Loki keeps it.

Both land in Grafana.
Two dashboards, eleven panels, one alert.
And the dashed arrow is the bit I care about — one click from a spike to the log lines behind it.
Without it, this is two tools sitting next to each other.

---

## 16. Two dashboards, eleven panels

Two dashboards, eleven panels.
Neither was clicked together by hand — they are JSON files in the repo.

Left is the app.
Right is what it runs on.

The panel I would defend is top right: it shows whether the collector can still reach everything.
If that goes to zero, every other graph goes quiet — and quiet looks exactly like healthy.

---

## 17. I attacked my own app, and it noticed

So I attacked my own app.
Normal traffic first, flat and boring.
Then I send it rubbish, three different kinds of broken, because the app refuses each one differently.

And the graph notices.
That is the point.
I did not go looking, it told me.

---

## 18. Now I get told instead of noticing

And then it alerts me.
One rule, written in code next to the dashboards.

It waits a full minute first.
One bad second should not wake anyone up, so it goes pending, and only becomes a real alert if the problem is still there a minute later.

This is also the answer to the thirty seven seconds.
Back then I only knew because I was watching.
This is the version of me that gets told.

---

## 19. One click, and I'm looking at why

From the red graph I click once, and it opens the actual log lines.
Already filtered to the failures, already at the right time.
I did not type a search.

A graph and a log viewer that do not talk to each other are two tools.
The link between them is what makes it one thing.

And every line has an ID for the request that made it, so I can pull one failed request out and see everything it did.

---

## 20. I attacked it on paper before anyone else could

Yesterday I sat down and attacked my own project on paper.
Nobody asked me to.
If I trust this thing to deploy for me, it is worth trying to break it first.

Nine problems.
Five fixed, with dates.
Four still open, written down with the reason.
A problem I decided not to fix yet is still better than one I forgot.

---

## 21. I defeated my own check to prove the other one

A check that has never failed is not a check.
So I proved the pipeline one by beating the one on my laptop, on purpose.

I made a fake AWS key, used the one flag that skips my local check, and pushed it.
The pipeline stopped it in eleven seconds.

---

## 22. Six things I chose not to build

What I did not build, and why.
None of these are things I forgot.

The honest one is the thirty seven seconds.
I know exactly how to fix it and it did not fit in the time.

---

## 23. Twice, I clicked past my own rule.

Two mistakes, same shape, three days apart.
Both were rules I had written down myself, and clicked straight past.

First, I merged something the wrong way, because the button remembered what I picked last time.
Second, for three days my work went to GitHub and never reached the machine that runs the pipeline.
Everything looked green, and what was running was three days old.

What I take from it is simple.
A rule that only lives in a document depends on me being careful, and I was not.
Both of these are what an enforced rule would have caught for me.

---

## 24. Four things, none of them tools

Four things I learned, and none of them are tools.

Sprints changed how I plan.
My first one had twice the work it should have.
I learned to cut early and say what I am cutting.

Second, go and ask what is expected.
My mentor said a written down limitation counts as an answer.
That saved me days.

Third, if I have not proved it, it is not done.
Half of this deck is me proving things I had already built, and every time, I found something.

Fourth, writing it down as I went is the only reason I can defend any of it now.

---

## 25. The unflattering number is the one worth leading with.

One thing about presenting, since this is the third time I have stood here.

After the first review I learned that showing a live run is a bad trade.
It is slow, it can fail, and it says less than a screenshot with someone explaining it.

The bigger one.
I used to want to show only the parts that worked.
What people actually took seriously was the thirty seven seconds, and the two rules I broke.

---

## 26. From "it works, I think" to "here's the proof."

The goal was a pipeline where a merge deploys exactly what was tested, checks it works, can be undone in under a minute, and tells me when something is wrong.
That is done, and I showed it instead of claiming it.

What I would want you to take away is not the tools.
It is that every number in here came off a run I can do again in front of you.

---


# If they ask — answers, per slide

Do not say these unless asked. They are here so you are not surprised.

**1. Project A**

- Say early that these are screenshots, not a live run. Reason: a live run is slow, it can break, and I would rather spend the time on what it produced. The stack is running behind this if you want to look after.

**3. Three sprints, one arc**

- If asked why watching came last: you cannot usefully watch something you cannot deploy properly. The order was on purpose.

**5. How fast can it tell me I'm wrong?**

- All of them are pinned to exact versions. A tool that changes its rules overnight turns a build red that nobody touched, and then people stop trusting red.

**6. One commit, all the way through**

- This is today's run, not an old one. So the picture and the pipeline file say the same thing. I will come back to why that matters.

**8. Now I can answer it in one command**

- Say the gap yourself: this reads a label off the container, so it needs Docker access. Asking the app over HTTP would be better. It is on the plan, not built.

**9. I tested one thing and shipped another.**

- The part I would defend hardest: that list checks if it has gone stale, and it went off within three days. A check that has never fired is a check you are guessing about.

**12. Nobody should be looking for a hash at 2am**

- It also left the broken container running on purpose so I can look at it, and said out loud not to treat it as live.

**13. 37 seconds down, not 8**

- If asked: the eight seconds does not include downloading the image, because the old one was already on the machine. On a fresh machine, add that.
- Then pause. You will want to fill the silence. Do not.

**15. Numbers on top, words underneath**

- If asked why Alloy instead of the app pushing logs itself: the app writes to standard output and knows nothing about Loki. I can swap the whole log stack out and never touch the application.

**17. I attacked my own app, and it noticed**

- Be precise: this is the app correctly refusing bad requests, not the app crashing. Telling those two apart on the graph is the next thing I would build.

**18. Now I get told instead of noticing**

- There is nowhere for it to go yet, no email, no message. Sending alerts I have not tested is worse than not sending them.

**19. One click, and I'm looking at why**

- If asked why that ID is not on the graphs too: graphs count things, and a new ID for every request would make a new counter for every request. That fills the disk. IDs go in logs, graphs stay simple. This is the most likely hard question, have it ready.

**20. I attacked it on paper before anyone else could**

- If asked which one bothers me: nothing actually stops someone overwriting an image in the registry. My pipeline never does it, but that is a habit, not a lock. Say it before they find it.

**21. I defeated my own check to prove the other one**

- Point at scanning 91 files. That line matters as much as the finding. It proves the scanner actually got something. A scanner pointed at an empty folder is green and useless.
- And the thing I got wrong, worth saying here: undoing that commit does not remove the password. The history looks clean and the key is still there, readable forever. The only real fix is changing the password. It looks like it worked, and that is what makes it dangerous.

**22. Six things I chose not to build**

- Careful with branch rules. I follow them, but the repo cannot enforce them on our plan. Do not suggest the button is blocked. Say plainly that I do it by hand.

**23. Twice, I clicked past my own rule.**

- Say you found both yourself, before today, and wrote both down. Then stop.

**25. The unflattering number is the one worth leading with.**

- Say the last line simply, then stop. Do not add anything after it.

**26. From "it works, I think" to "here's the proof."**

- If asked to run it live: the stack is up right now and I am happy to. Then thank them properly, because the feedback after each sprint is most of why this got better.
