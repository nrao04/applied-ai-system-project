# Reflection — comparing profiles

I ran `python -m src.main` a bunch of times with different fake users and tried to explain what moved in plain terms. If you’re not looking at the code, the idea is: same spreadsheet, different sliders, different top five.

## Pop (high energy) vs lofi (chill)

When I switch from the upbeat pop profile to the chill lofi one, the list stops trying to be loud and shiny. Lofi rows win because I turned on “likes acoustic,” so the scorer actually rewards tracks that are more acoustic. Stuff like Library Rain and Midnight Coding floats up. Pop was basically doing the opposite: it favors produced-sounding tracks, so the acoustic lofi picks never really had a shot there.

## Pop vs rock (intense)

Rock + intense mood pulls Storm Runner to the top instead of Sunrise City. Energy is still high in both profiles, but “happy” vs “intense” changes who gets the mood bonus. One thing that stuck out: Gym Hero is still pop, but it’s tagged intense, so it hangs around the rock list too. That’s not a bug so much as a reminder that one tag can drag a song into a list where the genre doesn’t match what you pictured.

## Lofi vs the weird “moody + max energy” profile

The chill profile keeps energy low, so soft tracks make sense. The adversarial one wants moody *and* almost max energy, which pulls the ranking in two directions. Night Drive Loop gets some love because it’s moody, but the really loud stuff wins on energy. Gym Hero ends up high again because it’s loud and still pop, even though it isn’t “moody” in the data. So you get these compromises that come from the tags being incomplete, not from the math being magic.

## Fiddling with weights

I messed with the genre vs energy weights in `recommender.py` for a bit (described in the README). When I downweighted genre and pushed energy harder, the ordering in the middle changed more than #1 did, because a few songs were already sitting close to the target energy. Felt like a good reality check: if you only tune one knob, you can end up with “everything sounds the same speed” even when the titles look different.
