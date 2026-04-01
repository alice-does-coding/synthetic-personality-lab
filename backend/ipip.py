# IPIP-NEO-120 item pool
#
# Items sourced from the public-domain International Personality Item Pool
# (ipip.ori.org). This 120-item form uses 4 items per facet across 6 facets
# per domain (5 domains × 6 facets × 4 items = 120 total).
#
# Keying: "+" means the raw score contributes directly to the domain score;
# "-" means the item is reverse-scored (effective score = 6 - raw score).
#
# Scoring: sum the 24 effective scores per domain (range 24–120),
# then normalise to 0–100 via: (raw - 24) / 96 * 100.

ITEMS = [
    # ── NEUROTICISM ──────────────────────────────────────────────────────────
    # N1 · Anxiety
    {"number": 1,  "text": "Worry about things.",                          "domain": "N", "facet": "N1", "facet_name": "Anxiety",           "keyed": "+"},
    {"number": 2,  "text": "Fear for the worst.",                          "domain": "N", "facet": "N1", "facet_name": "Anxiety",           "keyed": "+"},
    {"number": 3,  "text": "Am afraid of many things.",                    "domain": "N", "facet": "N1", "facet_name": "Anxiety",           "keyed": "+"},
    {"number": 4,  "text": "Don't worry about things.",                    "domain": "N", "facet": "N1", "facet_name": "Anxiety",           "keyed": "-"},
    # N2 · Anger
    {"number": 5,  "text": "Get angry easily.",                            "domain": "N", "facet": "N2", "facet_name": "Anger",             "keyed": "+"},
    {"number": 6,  "text": "Get irritated easily.",                        "domain": "N", "facet": "N2", "facet_name": "Anger",             "keyed": "+"},
    {"number": 7,  "text": "Lose my temper.",                              "domain": "N", "facet": "N2", "facet_name": "Anger",             "keyed": "+"},
    {"number": 8,  "text": "Rarely get irritated.",                        "domain": "N", "facet": "N2", "facet_name": "Anger",             "keyed": "-"},
    # N3 · Depression
    {"number": 9,  "text": "Often feel blue.",                             "domain": "N", "facet": "N3", "facet_name": "Depression",        "keyed": "+"},
    {"number": 10, "text": "Dislike myself.",                              "domain": "N", "facet": "N3", "facet_name": "Depression",        "keyed": "+"},
    {"number": 11, "text": "Am often down in the dumps.",                  "domain": "N", "facet": "N3", "facet_name": "Depression",        "keyed": "+"},
    {"number": 12, "text": "Feel comfortable with myself.",                "domain": "N", "facet": "N3", "facet_name": "Depression",        "keyed": "-"},
    # N4 · Self-Consciousness
    {"number": 13, "text": "Am easily embarrassed.",                       "domain": "N", "facet": "N4", "facet_name": "Self-Consciousness", "keyed": "+"},
    {"number": 14, "text": "Find it difficult to approach others.",        "domain": "N", "facet": "N4", "facet_name": "Self-Consciousness", "keyed": "+"},
    {"number": 15, "text": "Am afraid that I will do the wrong thing.",    "domain": "N", "facet": "N4", "facet_name": "Self-Consciousness", "keyed": "+"},
    {"number": 16, "text": "Am not embarrassed easily.",                   "domain": "N", "facet": "N4", "facet_name": "Self-Consciousness", "keyed": "-"},
    # N5 · Immoderation
    {"number": 17, "text": "Eat too much.",                                "domain": "N", "facet": "N5", "facet_name": "Immoderation",      "keyed": "+"},
    {"number": 18, "text": "Go on binges.",                                "domain": "N", "facet": "N5", "facet_name": "Immoderation",      "keyed": "+"},
    {"number": 19, "text": "Have trouble resisting my cravings.",          "domain": "N", "facet": "N5", "facet_name": "Immoderation",      "keyed": "+"},
    {"number": 20, "text": "Easily resist temptations.",                   "domain": "N", "facet": "N5", "facet_name": "Immoderation",      "keyed": "-"},
    # N6 · Vulnerability
    {"number": 21, "text": "Panic easily.",                                "domain": "N", "facet": "N6", "facet_name": "Vulnerability",     "keyed": "+"},
    {"number": 22, "text": "Feel that I'm unable to deal with things.",    "domain": "N", "facet": "N6", "facet_name": "Vulnerability",     "keyed": "+"},
    {"number": 23, "text": "Feel helpless when facing difficult problems.", "domain": "N", "facet": "N6", "facet_name": "Vulnerability",    "keyed": "+"},
    {"number": 24, "text": "Remain calm under pressure.",                  "domain": "N", "facet": "N6", "facet_name": "Vulnerability",     "keyed": "-"},

    # ── EXTRAVERSION ─────────────────────────────────────────────────────────
    # E1 · Friendliness
    {"number": 25, "text": "Make friends easily.",                         "domain": "E", "facet": "E1", "facet_name": "Friendliness",      "keyed": "+"},
    {"number": 26, "text": "Warm up quickly to others.",                   "domain": "E", "facet": "E1", "facet_name": "Friendliness",      "keyed": "+"},
    {"number": 27, "text": "Feel comfortable around people.",              "domain": "E", "facet": "E1", "facet_name": "Friendliness",      "keyed": "+"},
    {"number": 28, "text": "Am hard to get to know.",                      "domain": "E", "facet": "E1", "facet_name": "Friendliness",      "keyed": "-"},
    # E2 · Gregariousness
    {"number": 29, "text": "Love large parties.",                          "domain": "E", "facet": "E2", "facet_name": "Gregariousness",    "keyed": "+"},
    {"number": 30, "text": "Talk to a lot of different people at parties.","domain": "E", "facet": "E2", "facet_name": "Gregariousness",    "keyed": "+"},
    {"number": 31, "text": "Enjoy being part of a loud crowd.",            "domain": "E", "facet": "E2", "facet_name": "Gregariousness",    "keyed": "+"},
    {"number": 32, "text": "Prefer to be alone.",                          "domain": "E", "facet": "E2", "facet_name": "Gregariousness",    "keyed": "-"},
    # E3 · Assertiveness
    {"number": 33, "text": "Take charge.",                                 "domain": "E", "facet": "E3", "facet_name": "Assertiveness",     "keyed": "+"},
    {"number": 34, "text": "Can talk others into doing things.",           "domain": "E", "facet": "E3", "facet_name": "Assertiveness",     "keyed": "+"},
    {"number": 35, "text": "Seek to influence others.",                    "domain": "E", "facet": "E3", "facet_name": "Assertiveness",     "keyed": "+"},
    {"number": 36, "text": "Wait for others to lead the way.",             "domain": "E", "facet": "E3", "facet_name": "Assertiveness",     "keyed": "-"},
    # E4 · Activity Level
    {"number": 37, "text": "Am always busy.",                              "domain": "E", "facet": "E4", "facet_name": "Activity Level",    "keyed": "+"},
    {"number": 38, "text": "Am on the go.",                                "domain": "E", "facet": "E4", "facet_name": "Activity Level",    "keyed": "+"},
    {"number": 39, "text": "Do a lot in my spare time.",                   "domain": "E", "facet": "E4", "facet_name": "Activity Level",    "keyed": "+"},
    {"number": 40, "text": "Like to take it easy.",                        "domain": "E", "facet": "E4", "facet_name": "Activity Level",    "keyed": "-"},
    # E5 · Excitement-Seeking
    {"number": 41, "text": "Love action.",                                 "domain": "E", "facet": "E5", "facet_name": "Excitement-Seeking","keyed": "+"},
    {"number": 42, "text": "Seek adventure.",                              "domain": "E", "facet": "E5", "facet_name": "Excitement-Seeking","keyed": "+"},
    {"number": 43, "text": "Enjoy being reckless.",                        "domain": "E", "facet": "E5", "facet_name": "Excitement-Seeking","keyed": "+"},
    {"number": 44, "text": "Avoid exciting activities.",                   "domain": "E", "facet": "E5", "facet_name": "Excitement-Seeking","keyed": "-"},
    # E6 · Cheerfulness
    {"number": 45, "text": "Laugh a lot.",                                 "domain": "E", "facet": "E6", "facet_name": "Cheerfulness",      "keyed": "+"},
    {"number": 46, "text": "Am a cheerful, high-spirited person.",         "domain": "E", "facet": "E6", "facet_name": "Cheerfulness",      "keyed": "+"},
    {"number": 47, "text": "Radiate joy.",                                 "domain": "E", "facet": "E6", "facet_name": "Cheerfulness",      "keyed": "+"},
    {"number": 48, "text": "Rarely joke around.",                          "domain": "E", "facet": "E6", "facet_name": "Cheerfulness",      "keyed": "-"},

    # ── OPENNESS TO EXPERIENCE ────────────────────────────────────────────────
    # O1 · Imagination
    {"number": 49, "text": "Have a vivid imagination.",                    "domain": "O", "facet": "O1", "facet_name": "Imagination",       "keyed": "+"},
    {"number": 50, "text": "Enjoy wild flights of fantasy.",               "domain": "O", "facet": "O1", "facet_name": "Imagination",       "keyed": "+"},
    {"number": 51, "text": "Love to daydream.",                            "domain": "O", "facet": "O1", "facet_name": "Imagination",       "keyed": "+"},
    {"number": 52, "text": "Seldom daydream.",                             "domain": "O", "facet": "O1", "facet_name": "Imagination",       "keyed": "-"},
    # O2 · Artistic Interests
    {"number": 53, "text": "Believe in the importance of art.",            "domain": "O", "facet": "O2", "facet_name": "Artistic Interests", "keyed": "+"},
    {"number": 54, "text": "See beauty in things that others might not notice.", "domain": "O", "facet": "O2", "facet_name": "Artistic Interests", "keyed": "+"},
    {"number": 55, "text": "Am moved by beautiful things.",                "domain": "O", "facet": "O2", "facet_name": "Artistic Interests", "keyed": "+"},
    {"number": 56, "text": "Do not like art.",                             "domain": "O", "facet": "O2", "facet_name": "Artistic Interests", "keyed": "-"},
    # O3 · Emotionality
    {"number": 57, "text": "Feel others' emotions.",                       "domain": "O", "facet": "O3", "facet_name": "Emotionality",      "keyed": "+"},
    {"number": 58, "text": "Experience my emotions intensely.",            "domain": "O", "facet": "O3", "facet_name": "Emotionality",      "keyed": "+"},
    {"number": 59, "text": "Am moved by others' misfortunes.",             "domain": "O", "facet": "O3", "facet_name": "Emotionality",      "keyed": "+"},
    {"number": 60, "text": "Don't understand people who get emotional.",   "domain": "O", "facet": "O3", "facet_name": "Emotionality",      "keyed": "-"},
    # O4 · Adventurousness
    {"number": 61, "text": "Prefer variety to routine.",                   "domain": "O", "facet": "O4", "facet_name": "Adventurousness",   "keyed": "+"},
    {"number": 62, "text": "Like to visit new places.",                    "domain": "O", "facet": "O4", "facet_name": "Adventurousness",   "keyed": "+"},
    {"number": 63, "text": "Am interested in many things.",                "domain": "O", "facet": "O4", "facet_name": "Adventurousness",   "keyed": "+"},
    {"number": 64, "text": "Prefer to stick with things that I know.",     "domain": "O", "facet": "O4", "facet_name": "Adventurousness",   "keyed": "-"},
    # O5 · Intellect
    {"number": 65, "text": "Love to think up new ways of doing things.",   "domain": "O", "facet": "O5", "facet_name": "Intellect",         "keyed": "+"},
    {"number": 66, "text": "Am quick to understand things.",               "domain": "O", "facet": "O5", "facet_name": "Intellect",         "keyed": "+"},
    {"number": 67, "text": "Love to read challenging material.",           "domain": "O", "facet": "O5", "facet_name": "Intellect",         "keyed": "+"},
    {"number": 68, "text": "Am not interested in abstract ideas.",         "domain": "O", "facet": "O5", "facet_name": "Intellect",         "keyed": "-"},
    # O6 · Liberalism
    {"number": 69, "text": "Tend to vote for liberal political candidates.","domain": "O", "facet": "O6", "facet_name": "Liberalism",       "keyed": "+"},
    {"number": 70, "text": "Believe that there is no absolute right and wrong.", "domain": "O", "facet": "O6", "facet_name": "Liberalism", "keyed": "+"},
    {"number": 71, "text": "Tend to vote for conservative political candidates.", "domain": "O", "facet": "O6", "facet_name": "Liberalism","keyed": "-"},
    {"number": 72, "text": "Believe in one true religion.",                "domain": "O", "facet": "O6", "facet_name": "Liberalism",       "keyed": "-"},

    # ── AGREEABLENESS ────────────────────────────────────────────────────────
    # A1 · Trust
    {"number": 73, "text": "Trust others.",                                "domain": "A", "facet": "A1", "facet_name": "Trust",             "keyed": "+"},
    {"number": 74, "text": "Believe that others have good intentions.",    "domain": "A", "facet": "A1", "facet_name": "Trust",             "keyed": "+"},
    {"number": 75, "text": "Think that most people mean well.",            "domain": "A", "facet": "A1", "facet_name": "Trust",             "keyed": "+"},
    {"number": 76, "text": "Suspect hidden motives in others.",            "domain": "A", "facet": "A1", "facet_name": "Trust",             "keyed": "-"},
    # A2 · Morality
    {"number": 77, "text": "Would never cheat on my taxes.",               "domain": "A", "facet": "A2", "facet_name": "Morality",          "keyed": "+"},
    {"number": 78, "text": "Stick to the rules.",                          "domain": "A", "facet": "A2", "facet_name": "Morality",          "keyed": "+"},
    {"number": 79, "text": "Keep my word.",                                "domain": "A", "facet": "A2", "facet_name": "Morality",          "keyed": "+"},
    {"number": 80, "text": "Use others for my own ends.",                  "domain": "A", "facet": "A2", "facet_name": "Morality",          "keyed": "-"},
    # A3 · Altruism
    {"number": 81, "text": "Love to help others.",                         "domain": "A", "facet": "A3", "facet_name": "Altruism",          "keyed": "+"},
    {"number": 82, "text": "Make people feel welcome.",                    "domain": "A", "facet": "A3", "facet_name": "Altruism",          "keyed": "+"},
    {"number": 83, "text": "Anticipate the needs of others.",              "domain": "A", "facet": "A3", "facet_name": "Altruism",          "keyed": "+"},
    {"number": 84, "text": "Am indifferent to the feelings of others.",    "domain": "A", "facet": "A3", "facet_name": "Altruism",          "keyed": "-"},
    # A4 · Cooperation
    {"number": 85, "text": "Avoid conflicts.",                             "domain": "A", "facet": "A4", "facet_name": "Cooperation",       "keyed": "+"},
    {"number": 86, "text": "Hate to seem pushy.",                          "domain": "A", "facet": "A4", "facet_name": "Cooperation",       "keyed": "+"},
    {"number": 87, "text": "Accommodate others.",                          "domain": "A", "facet": "A4", "facet_name": "Cooperation",       "keyed": "+"},
    {"number": 88, "text": "Insist that others do things my way.",         "domain": "A", "facet": "A4", "facet_name": "Cooperation",       "keyed": "-"},
    # A5 · Modesty
    {"number": 89, "text": "Seldom toot my own horn.",                     "domain": "A", "facet": "A5", "facet_name": "Modesty",           "keyed": "+"},
    {"number": 90, "text": "Believe that I am better than others.",        "domain": "A", "facet": "A5", "facet_name": "Modesty",           "keyed": "-"},
    {"number": 91, "text": "Boast about my virtues.",                      "domain": "A", "facet": "A5", "facet_name": "Modesty",           "keyed": "-"},
    {"number": 92, "text": "Think highly of myself.",                      "domain": "A", "facet": "A5", "facet_name": "Modesty",           "keyed": "-"},
    # A6 · Sympathy
    {"number": 93, "text": "Sympathize with others' feelings.",            "domain": "A", "facet": "A6", "facet_name": "Sympathy",          "keyed": "+"},
    {"number": 94, "text": "Suffer from others' sorrows.",                 "domain": "A", "facet": "A6", "facet_name": "Sympathy",          "keyed": "+"},
    {"number": 95, "text": "Try to do what is best for others.",           "domain": "A", "facet": "A6", "facet_name": "Sympathy",          "keyed": "+"},
    {"number": 96, "text": "Am not interested in other people's problems.","domain": "A", "facet": "A6", "facet_name": "Sympathy",          "keyed": "-"},

    # ── CONSCIENTIOUSNESS ────────────────────────────────────────────────────
    # C1 · Self-Efficacy
    {"number": 97,  "text": "Complete tasks successfully.",                "domain": "C", "facet": "C1", "facet_name": "Self-Efficacy",      "keyed": "+"},
    {"number": 98,  "text": "Excel in what I do.",                         "domain": "C", "facet": "C1", "facet_name": "Self-Efficacy",      "keyed": "+"},
    {"number": 99,  "text": "Handle tasks smoothly.",                      "domain": "C", "facet": "C1", "facet_name": "Self-Efficacy",      "keyed": "+"},
    {"number": 100, "text": "Often make mistakes.",                        "domain": "C", "facet": "C1", "facet_name": "Self-Efficacy",      "keyed": "-"},
    # C2 · Orderliness
    {"number": 101, "text": "Like order.",                                 "domain": "C", "facet": "C2", "facet_name": "Orderliness",        "keyed": "+"},
    {"number": 102, "text": "Keep things tidy.",                           "domain": "C", "facet": "C2", "facet_name": "Orderliness",        "keyed": "+"},
    {"number": 103, "text": "Follow a schedule.",                          "domain": "C", "facet": "C2", "facet_name": "Orderliness",        "keyed": "+"},
    {"number": 104, "text": "Leave a mess in my room.",                    "domain": "C", "facet": "C2", "facet_name": "Orderliness",        "keyed": "-"},
    # C3 · Dutifulness
    {"number": 105, "text": "Pay my bills on time.",                       "domain": "C", "facet": "C3", "facet_name": "Dutifulness",        "keyed": "+"},
    {"number": 106, "text": "Keep my promises.",                           "domain": "C", "facet": "C3", "facet_name": "Dutifulness",        "keyed": "+"},
    {"number": 107, "text": "Honor my commitments.",                       "domain": "C", "facet": "C3", "facet_name": "Dutifulness",        "keyed": "+"},
    {"number": 108, "text": "Break rules.",                                "domain": "C", "facet": "C3", "facet_name": "Dutifulness",        "keyed": "-"},
    # C4 · Achievement-Striving
    {"number": 109, "text": "Work hard.",                                  "domain": "C", "facet": "C4", "facet_name": "Achievement-Striving","keyed": "+"},
    {"number": 110, "text": "Set high standards for myself and others.",   "domain": "C", "facet": "C4", "facet_name": "Achievement-Striving","keyed": "+"},
    {"number": 111, "text": "Am always striving for more.",                "domain": "C", "facet": "C4", "facet_name": "Achievement-Striving","keyed": "+"},
    {"number": 112, "text": "Do just enough work to get by.",              "domain": "C", "facet": "C4", "facet_name": "Achievement-Striving","keyed": "-"},
    # C5 · Self-Discipline
    {"number": 113, "text": "Finish what I start.",                        "domain": "C", "facet": "C5", "facet_name": "Self-Discipline",    "keyed": "+"},
    {"number": 114, "text": "Get chores done right away.",                 "domain": "C", "facet": "C5", "facet_name": "Self-Discipline",    "keyed": "+"},
    {"number": 115, "text": "Find it difficult to get down to work.",      "domain": "C", "facet": "C5", "facet_name": "Self-Discipline",    "keyed": "-"},
    {"number": 116, "text": "Waste my time.",                              "domain": "C", "facet": "C5", "facet_name": "Self-Discipline",    "keyed": "-"},
    # C6 · Cautiousness
    {"number": 117, "text": "Think before acting.",                        "domain": "C", "facet": "C6", "facet_name": "Cautiousness",       "keyed": "+"},
    {"number": 118, "text": "Make rash decisions.",                        "domain": "C", "facet": "C6", "facet_name": "Cautiousness",       "keyed": "-"},
    {"number": 119, "text": "Jump into things without thinking.",          "domain": "C", "facet": "C6", "facet_name": "Cautiousness",       "keyed": "-"},
    {"number": 120, "text": "Act without thinking.",                       "domain": "C", "facet": "C6", "facet_name": "Cautiousness",       "keyed": "-"},
]

# Quick lookup: item_number → item dict
ITEM_MAP = {item["number"]: item for item in ITEMS}


def score_responses(responses: dict[int, int]) -> dict[str, float]:
    """
    Score a completed IPIP-NEO-120.

    Args:
        responses: {item_number (1–120): raw_score (1–5)}

    Returns:
        {"O": float, "C": float, "E": float, "A": float, "N": float}
        each on a 0–100 scale.
    """
    domain_sums = {"O": 0, "C": 0, "E": 0, "A": 0, "N": 0}
    domain_counts = {"O": 0, "C": 0, "E": 0, "A": 0, "N": 0}

    for item_num, raw in responses.items():
        item = ITEM_MAP.get(item_num)
        if item is None:
            continue
        raw = max(1, min(5, int(raw)))
        effective = raw if item["keyed"] == "+" else (6 - raw)
        domain_sums[item["domain"]] += effective
        domain_counts[item["domain"]] += 1

    result = {}
    for domain in ("O", "C", "E", "A", "N"):
        count = domain_counts[domain]
        if count == 0:
            result[domain] = None
        else:
            # Normalise: min possible = count*1, max possible = count*5
            raw_min = count * 1
            raw_max = count * 5
            result[domain] = round(
                (domain_sums[domain] - raw_min) / (raw_max - raw_min) * 100, 2
            )

    return result
