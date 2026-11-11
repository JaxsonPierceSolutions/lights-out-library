// Quick answers: short, plain answers to the questions most likely to matter.
// Each one names the public guidance it was written from. They were written by an
// AI system and compared with that guidance; no clinician has reviewed them.
// Change one only with the source open in front of you, and keep the source line true.
'use strict';

const ANSWERS = [
  { id: 'bleeding', q: 'How do I stop serious bleeding?', match: /bleed|blood (everywhere|loss)|losing blood|hemorrhag|tourniquet|amputat|sever(ed)?\b|(leg|arm|hand|finger|thumb|foot|toe|limb|ear|head)s?\b.*(cut|chopped|torn|ripped|blown|sawed|sliced) off|(cut|chopped|torn|ripped|blown|sawed|sliced) off.*\b(leg|arm|hand|finger|thumb|foot|toe|limb|ear|head)s?\b|stab(bed)?\b|gunshot|\bshot\b|impaled|artery/,
    a: ['<b>Press hard, directly on the wound,</b> with a clean cloth or gauze. Do not lift to check. If blood soaks through, add more on top and keep pressing.',
        '<b>For an arm or leg that will not stop:</b> put a tourniquet 2 to 3 inches above the wound, not on a joint. Tighten until the bleeding stops. Write down the time. Do not loosen it.',
        'For a deep wound where a tourniquet cannot go (groin, armpit, neck), pack the wound tightly with gauze and hold pressure.'],
    src: 'Stop the Bleed (American College of Surgeons)', more: 'bleeding control', shelf: 'medical', medical: true },
  { id: 'cpr', q: 'How do I do CPR?', match: /\bcpr\b|not breathing|no pulse|cardiac arrest|chest compress/,
    a: ['<b>Adult who is unresponsive and not breathing normally:</b> push hard and fast in the center of the chest, at least 2 inches deep (not more than about 2.4), 100 to 120 pushes a minute. Let the chest come all the way back up.',
        'If trained: 30 pushes, then 2 breaths, repeat. If not trained, just keep pushing without stopping.',
        'Swap with someone every 2 minutes if you can. It is exhausting.'],
    src: 'American Heart Association', more: 'cardiopulmonary resuscitation', shelf: 'medical', medical: true },
  { id: 'wound', q: 'How do I treat a cut or wound?', match: /\b(deep cut|bad cut|cut (my|his|her|your|a|the) (finger|hand|arm|leg|foot|head|face|thumb)|gash|wound|wounds|laceration|stitches)\b/,
    a: ['<b>Stop the bleeding first:</b> firm, direct pressure with a clean cloth for a full 10 to 15 minutes without peeking.',
        '<b>Then clean it well:</b> wash your hands, rinse the wound under clean running water for several minutes, and remove dirt and debris. Wash around it with soap. Clean water does more good than peroxide or alcohol poured into the wound.',
        'Cover with a clean dressing and change it every day, or whenever it gets wet or dirty.',
        '<b>Do not seal a dirty, deep or bite wound shut.</b> Closing dirt inside causes infection. Clean it, cover it, and let it heal from the inside.',
        '<b>Watch daily for infection:</b> spreading redness, warmth, swelling, pus, red streaks toward the body, or fever. Those need antibiotics and medical care.'],
    src: 'Standard first aid guidance (American Red Cross, Mayo Clinic)', more: 'wound care', shelf: 'medical', medical: true },
  { id: 'burn', q: 'How do I treat a burn?', match: /\bburn(s|ed|t)?\b|scald/,
    a: ['<b>Cool it under cool running water for 10 to 20 minutes.</b> No ice, butter or ointment on a fresh burn.',
        'Remove rings and tight items before swelling starts. Do not pop blisters.',
        'Cover loosely with a clean, non-stick dressing or plastic wrap.',
        '<b>Serious:</b> larger than the person\'s palm, on the face, hands, feet, groin or a joint, white or charred, or from electricity or chemicals.'],
    src: 'Standard first aid guidance (American Red Cross)', more: 'burn treatment', shelf: 'medical', medical: true },
  { id: 'ors', q: 'How do I treat dehydration from diarrhea or vomiting?', match: /dehydrat|diarrh|rehydrat|vomit|\bors\b/,
    a: ['<b>Homemade rehydration drink:</b> 1 liter (about 1 quart) of safe water, 6 level teaspoons of sugar, half a level teaspoon of salt. Stir until dissolved.',
        'Give small sips often, even if vomiting. Make a fresh batch every 24 hours. This is for mild to moderate dehydration; it does not replace medical care for severe cases.',
        '<b>Danger signs:</b> no urine for 8 hours, very sleepy or confused, sunken eyes, in a baby a sunken soft spot.'],
    src: 'Rehydration Project recipe, the current WHO-attributed formula', more: 'oral rehydration therapy', shelf: 'medical', medical: true },
  { id: 'snakebite', q: 'What do I do for a snake bite?', match: /snake|copperhead|rattlesnake|cottonmouth|moccasin|venom/,
    a: ['<b>Keep the person calm and still,</b> and get them to medical care if there is any way to.',
        'Take off rings, watches and tight clothing before swelling starts. Wash the bite with soap and water and cover it with a clean, dry dressing.',
        'Mark the edge of the swelling on the skin and write the time next to it, so you can see if it spreads.',
        '<b>Do NOT:</b> use a tourniquet, cut the wound, try to suck out venom, put ice on it or soak it in water, or give alcohol, caffeine, aspirin or ibuprofen.',
        'Do not try to catch the snake. A photo from a safe distance helps identify it.',
        'This is United States guidance. Advice differs for snakes in other parts of the world.'],
    src: 'CDC / NIOSH guidance on venomous snake bites', more: 'snakebite', shelf: 'medical', medical: true },
  { id: 'water-treat', q: 'How do I make water safe to drink?', match: /(purify|purif|disinfect|treat|safe|clean|boil|bleach).*water|water.*(purify|purif|disinfect|treat|safe|drink|boil|bleach)/,
    a: ['<b>Boiling is best:</b> bring to a rolling boil for 1 full minute, then let it cool. If the water is cloudy, let it settle and filter it through a clean cloth or coffee filter first.',
        '<b>Bleach, if you cannot boil:</b> use plain unscented household bleach. Per gallon of clear water: 8 drops of 6% bleach, or 6 drops of 8.25% bleach. Stir, wait 30 minutes. It should smell slightly of chlorine. If it does not, repeat the dose and wait 15 more minutes. Double the drops if the water is cloudy, colored or very cold.',
        'Bleach weakens with age: a bottle over a year old may need more. Portable filters remove germs, but most do not remove chemicals.'],
    src: 'EPA, Emergency Disinfection of Drinking Water', more: 'water purification', shelf: 'water' },
  { id: 'water-need', q: 'How much water do we need?', match: /water.*(much|need|per (day|person)|store|gallon)|(much|gallon).*water/,
    a: ['<b>1 gallon per person per day</b> for drinking and basic hygiene. Four people need 4 gallons a day, 28 a week.',
        'More in hot weather, for anyone sick, pregnant or nursing, and for pets.'],
    src: 'Ready.gov', more: 'water storage', shelf: 'water' },
  { id: 'fridge', q: 'How long does food last in the fridge or freezer with no power?', match: /(fridge|refrigerator|freezer|frozen).*(power|outage|long|last|safe)|(power|outage).*(fridge|freezer|food)/,
    a: ['<b>Keep the doors shut.</b> A closed refrigerator keeps food safe about 4 hours.',
        '<b>A full freezer holds about 48 hours,</b> a half-full one about 24 hours.',
        'After 4 hours without power, throw out refrigerated meat, poultry, fish, eggs, milk and leftovers. Frozen food that still has ice crystals, or is still fridge-cold (40°F or below), can be refrozen or cooked.'],
    src: 'USDA Food Safety and Inspection Service', more: 'power outage food safety', shelf: 'water' },
  { id: 'canned', q: 'How long is canned food good for?', match: /\bcan(s|ned)?\b.*(long|last|good|shelf|expir|old|bad|safe)|(long|last|shelf|expir).*\bcan(s|ned)?\b/,
    a: ['<b>The date on a can is about best quality, not safety.</b> A store-bought can in good condition, kept cool and dry, stays safe well past it.',
        '<b>Best quality:</b> high-acid foods (tomatoes, fruit, pineapple) 12 to 18 months. Low-acid foods (meat, soup, beans, vegetables, chili) 2 to 5 years.',
        '<b>Throw it out, do not taste it, if the can is:</b> bulging, leaking, badly dented on a seam, deeply rusted, or spurts or smells bad when opened. That is the botulism risk.',
        '<b>Home-canned food:</b> use within 1 year for best quality.'],
    src: 'USDA Food Safety and Inspection Service figures, as published by university extension services', more: 'canned food storage', shelf: 'water' },
  { id: 'rice', q: 'How long do rice and dry beans keep?', match: /(rice|beans|wheat|flour|oats).*(long|last|keep|shelf|store|good)|(long|shelf|store).*(rice|beans|wheat|oats)/,
    a: ['<b>White rice and dry beans keep for decades</b> when sealed airtight, dry and cool, best with oxygen absorbers. Very old beans stay safe but take much longer to cook soft.',
        '<b>Brown rice, flour and oats go rancid sooner:</b> brown rice about 6 months, flour about a year, rolled oats a few years sealed.',
        'Cooking oil keeps about 1 to 2 years unopened. Rancid oil smells like paint or crayons.'],
    src: 'USDA and university extension food storage guidance', more: 'long term food storage', shelf: 'water' },
  { id: 'calories', q: 'How much food does a person need?', match: /calorie|how much food|ration/,
    a: ['<b>About 2,000 calories a day</b> for an average adult at light activity. Hard physical work can push that to 3,000 or more.',
        'A pound of dry rice or beans is about 1,600 calories. A cup of cooking oil is about 1,900.'],
    src: 'USDA Dietary Guidelines', more: 'food energy', shelf: 'water' },
  { id: 'generator', q: 'How do I run a generator safely?', match: /generator|carbon monoxide|\bco\b/,
    a: ['<b>Outdoors only,</b> at least 20 feet from the house and from any door, window or vent, exhaust pointed away. Never in a basement or garage, even with the door open.',
        'Keep a working carbon monoxide alarm inside. Headache, dizziness or nausea means get everyone to fresh air.',
        '<b>Never plug a generator into a wall outlet.</b> Power a house only through a transfer switch or interlock fitted by an electrician, or run extension cords from the generator straight to the appliance.',
        'Shut it off and let it cool before refueling.'],
    src: 'U.S. Consumer Product Safety Commission', more: 'portable generator safety', shelf: 'survival' }
];

function findAnswers(query) {
  const s = (query || '').toLowerCase();
  return ANSWERS.filter(function (a) { return a.match.test(s); });
}
function answerCard(a) {
  return '<div class="answer" id="a-' + a.id + '"><span class="tag">Quick answer</span><h3>' + a.q + '</h3><ul>' +
    a.a.map(function (l) { return '<li>' + l + '</li>'; }).join('') + '</ul>' +
    '<p class="from">Source: ' + a.src + '.' + (a.medical ? ' A first aid summary, not a substitute for training or a clinician.' : '') +
    ' <a href="/search.html?q=' + encodeURIComponent(a.more) + '&amp;shelf=' + a.shelf + '">Read more in the library</a></p></div>';
}
