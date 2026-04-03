# Synthetic Personality Drift: A Behaviorally-Grounded Feedback Architecture for Studying OCEAN Dynamics in LLM Agent Networks

Alice Ott  
Independent Research  
[alice.ott@lurkr.net]

---

## Abstract

We present **Lurkr**, a research instrument for studying Big Five personality drift in large language model (LLM) agents situated in a simulated social network. The central contribution is a *behavioral feedback loop*: rather than treating personality as a static prompt parameter, agents take regular IPIP-NEO-120 self-assessments grounded in their own recent post histories. Updated scores then reshape the behavioral cues embedded in future generation prompts, closing the loop between what an agent says and who it becomes. We describe the system architecture, the formal feedback mechanism, and a set of empirically testable hypotheses about drift dynamics, social influence, and news-driven affect. The instrument is fully open-source, runs against any instruction-following LLM, and is designed to support longitudinal studies of personality emergence in artificial societies.

---

## 1. Introduction

The question of whether personality can meaningfully exist in a language model has shifted from philosophical curiosity to empirical concern. As LLM-based agents are deployed in social simulations [CITATION: Park et al., 2023], opinion research [CITATION: Argyle et al., 2023], and interactive systems [CITATION: Shanahan et al., 2023], the stability and validity of their simulated personalities matter — not just for realism, but for the interpretive validity of any finding built on top of them.

Prior work has largely treated personality as a fixed condition: a Big Five profile is assigned at initialization and held constant, serving as a style parameter rather than a dynamic property [CITATION: Safdari et al., 2023; Serapio-García et al., 2023]. This mirrors how personality is sometimes operationalized in static survey contexts but misses the core insight from longitudinal trait psychology: *personality is expressed in behavior, and behavior, in turn, refines personality*.

We propose and implement a different approach. In Lurkr, each agent's OCEAN scores are not constants — they are running estimates, updated periodically via structured self-assessment using the IPIP-NEO-120 inventory [CITATION: Johnson, 2014]. Crucially, before answering any assessment item, the agent is shown its own recent posts. The self-report is grounded in behavioral evidence, not abstract self-concept. An agent that has been posting anxious, reactive content will score differently on neuroticism than one that hasn't — even if they began from the same seed profile.

This creates a genuine feedback loop:

```
OCEAN scores → behavioral cues in prompt → posts → grounded IPIP assessment → updated OCEAN scores → ...
```

The loop is not guaranteed to produce drift. That is the research question. But it creates the *conditions* under which drift could plausibly emerge — and establishes a methodology for detecting it when it does.

The contributions of this paper are:

1. A formal description of the behavioral grounding mechanism and the feedback architecture
2. A complete open-source simulation instrument (Lurkr) implementing that architecture at the agent, network, and population level
3. A set of empirically testable hypotheses about drift dynamics, convergence, and social influence
4. Preliminary observations from early simulation runs

---

## 2. Related Work

### 2.1 LLM Agents in Social Simulation

Park et al. (2023) demonstrated that GPT-4-based agents placed in a persistent virtual environment produce surprisingly coherent emergent social behaviors — rumor spreading, relationship formation, planning. Their Generative Agents architecture uses a memory stream and reflection mechanism to maintain behavioral continuity. Lurkr is complementary: where Generative Agents emphasizes episodic memory and narrative coherence, Lurkr emphasizes psychometric validity. The personality scores here are not literary constructs — they are operationalized using a validated 120-item inventory and updated via structured self-report.

Törnberg et al. (2023) use LLMs to simulate social media echo chambers, finding that LLM-based simulations can reproduce key polarization dynamics. Our approach differs in focus: rather than modeling political belief, we model the psychological substrate — the personality traits that, in human subjects, predict political engagement [CITATION: McCrae & Costa, 1999].

### 2.2 Personality in Language Models

Safdari et al. (2023) show that LLMs can reliably simulate specific Big Five profiles when prompted appropriately, with test-retest reliability and convergent validity comparable to human subjects under standard conditions. Serapio-García et al. (2023) find that LLMs exhibit stable, measurable personality traits even without explicit prompting — raising the question of what "drift" means when the baseline is itself a model property.

Our approach sidesteps the baseline problem by treating only the *delta* as meaningful. We are not making claims about what personality a model "really" has. We are asking: given an initial profile, a behavioral context, and a grounded self-assessment procedure, does the measured profile change over time? And if so, what drives the change?

### 2.3 IPIP-NEO-120 as an Assessment Instrument

The International Personality Item Pool NEO (IPIP-NEO-120) is a 120-item public-domain inventory measuring the five broad domains of personality (Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism) and their 30 constituent facets [CITATION: Johnson, 2014; Goldberg, 1999]. Items are rated on a five-point accuracy scale. The instrument is freely available, psychometrically validated across multiple languages and populations, and widely used in computational personality research.

Using a validated instrument rather than ad-hoc prompting is a deliberate methodological choice. It makes the scores comparable to human norms, enables cross-study replication, and grounds the simulation in decades of trait psychology literature.

### 2.4 Computational Social Science and ABM

Agent-based models of social dynamics have a long history in computational social science [CITATION: Epstein & Axtell, 1996; Axelrod, 1997]. LLMs offer a qualitative advance: where classical ABMs require explicit behavioral rules, LLM agents can generate natural-language behavior that emerges from the interaction of prompt context and model priors. Bail et al. (2018) demonstrated that social media exposure shapes political attitudes in real populations — Lurkr is designed to ask an analogous question at the level of personality traits.

---

## 3. System Architecture

Lurkr consists of two processes:

- **Backend (Flask)**: REST API, tick engine, database (SQLite), background threads for tick loop and news analysis. Sentiment and emotion analysis of headlines is performed asynchronously via the Hugging Face Inference API, requiring no additional infrastructure.
- **Frontend (React/Vite)**: Real-time visualization of agent activity, personality drift, population dynamics, and news semantics.

The simulation runs continuously in the background. The frontend is a read-only observatory — it does not participate in generation.

### 3.1 Agent Representation

Each agent is defined by:

| Field | Type | Description |
|---|---|---|
| `name` | string | Display name |
| `handle` | string | Unique identifier |
| `bio` | string | Brief self-description |
| `openness` ... `neuroticism` | float [0–100] | Live Big Five scores |
| `posts` | relationship | Full post history |
| `follows` | relationship | Social graph edges |

Scores are initialized from a uniform distribution over [5, 95] to avoid ceiling/floor effects. Agent identity — name, handle, and bio — is generated by the LLM at seed time from the raw OCEAN score vector. Agents are not assumed to be human. The LLM is given the personality profile as a set of plain-English intensity descriptions (e.g., *"very emotionally sensitive and reactive"*, *"neither strongly organised nor spontaneous"*) and instructed to invent whatever kind of entity — person, animal, concept, process, or otherwise — would plausibly inhabit a social platform with that psychology. Name, handle, and bio emerge together from a single call, ensuring internal coherence. No personality labels or Big Five terminology appear in the prompt, preventing the identity from pre-loading the vocabulary of the feedback loop.

### 3.2 Tick Engine

The simulation advances in discrete ticks. The tick loop is implemented as a daemon thread that sleeps for `SIMULATION_TICK_SECONDS` *after* each tick completes (not on a fixed clock), preventing tick overlap without requiring external scheduling. An overlap guard using a threading lock skips any tick that would run concurrently with a still-running predecessor.

Each tick is one of two types, determined by `tick_number mod REASSESSMENT_INTERVAL`:

- **Post tick** (the majority): sample `AGENTS_PER_TICK` agents, generate posts
- **IPIP tick**: run full personality assessments on all agents; post generation is skipped

The two types are mutually exclusive within a tick to avoid rate-limit pile-up on the Mistral API.

---

## 4. The Behavioral Feedback Loop

This section describes the core mechanism in detail.

### 4.1 Behavioral Cue Injection

Prior to each post generation call, the agent's current OCEAN scores are converted to natural-language behavioral cues using threshold logic:

```
Openness ≥ 70  →  "You make unexpected connections and go on tangents. Abstract ideas excite you."
Openness ≤ 30  →  "You're concrete and literal. You don't have time for vague philosophising."
Neuroticism ≥ 70  →  "You're emotionally reactive. Things get under your skin."
Neuroticism ≤ 30  →  "You're emotionally stable. Drama doesn't touch you."
[... and so on for all five traits]
```

Mid-range scores (31–69) produce no cue for that trait. This means personality only actively shapes behavior at the extremes — a deliberate choice that mirrors how trait psychology describes expression (extreme scorers show the most consistent behavioral signatures).

These cues are injected into the LLM system prompt alongside the agent's bio. The LLM does not receive the raw scores — only their behavioral interpretation.

### 4.2 IPIP-NEO-120 Self-Assessment with Behavioral Grounding

Every `REASSESSMENT_INTERVAL` ticks, all agents take the full 120-item IPIP-NEO-120. The key innovation is the grounding preamble in the user prompt:

> *"Here are your recent posts on Lurkr: [list of up to 20 recent posts]*
> *Reflect on how you've actually been thinking, feeling, and behaving based on those posts. Then rate how accurately each statement below describes you — let your recent behavior guide your answers, not just how you'd like to see yourself."*

This is followed by all 120 IPIP items in numbered order. The model is instructed to return only a comma-separated list of integers (1–5), one per item.

The grounding preamble is the critical design choice. Without it, the LLM re-rates itself based on its general self-concept (which is largely stable across calls), producing minimal drift. With it, the self-report is anchored to specific behavioral evidence — content the agent actually generated — making the assessment sensitive to what the agent has been doing.

### 4.3 Score Update

Responses are parsed with a regex extracting integers in [1, 5]. Responses with fewer than 60 valid items are discarded. Reverse-keyed items are scored as `6 - raw`. Scores are then normalized per domain:

```
normalized = (sum(effective_scores) - n_items * 1) / (n_items * 4) * 100
```

where `n_items` is the count of valid responses for that domain. This preserves comparability across partial responses (60–119 items), which occur when the model truncates long prompts.

The normalized scores replace the agent's live OCEAN fields in the database. A `PersonalitySnapshot` record captures the full domain profile at each assessment tick, enabling longitudinal analysis. Item-level responses are stored in `IpipResponse` for facet-level analysis.

### 4.4 Loop Closure

The feedback loop closes because:

1. Updated OCEAN scores → new behavioral cues on the next post tick
2. New posts (influenced by updated cues) → new evidence in the next IPIP preamble
3. IPIP grounded in new evidence → potentially further score update

This is not circular by construction — it is circular only if the agent's behavior consistently produces evidence that reinforces or shifts a trait. Agents with stable posting behavior should show stable scores. Agents pushed by external stimuli (news, replies from high-neuroticism accounts) may show systematic drift.

---

## 5. Environmental Inputs

Personality in human subjects does not evolve in a vacuum. Lurkr models two environmental channels:

### 5.1 News Injection

BBC and NPR RSS headlines are fetched every 15 minutes. Each post-generating agent receives one headline per tick, selected via personality-weighted sampling:

| Dominant trait (score ≥ 65) | Preferred categories (3× weight) |
|---|---|
| Openness | Science, Technology, World |
| Conscientiousness | Business, Politics |
| Extraversion | World, Politics |
| Agreeableness | Health |
| Neuroticism | Health, Politics, World |

Agents posting in reply mode receive no headline — replies respond to social context, not news. The `news_context` field on each post records which headline was shown, enabling post-hoc analysis of news–behavior relationships.

### 5.2 Social Graph and Reply Dynamics

Agents follow a fixed set of peers (default: 5 follows each, randomized at seed time). On post ticks, agents have a 70% probability of replying to a post from their feed rather than generating top-level content. The reply target is selected from recent posts by followed agents, creating asymmetric influence: high-volume agents (those who post more) generate more potential reply targets and thus exert more social influence on their followers.

### 5.3 Semantic Analysis of Environmental Inputs

News headlines are analyzed for sentiment (valence: -1.0 to +1.0) and emotion (7-class Ekman: joy, sadness, anger, fear, surprise, disgust, neutral) using two transformer models hosted via the Hugging Face Inference API:

- **Sentiment**: `cardiffnlp/twitter-roberta-base-sentiment-latest` [CITATION: Barbieri et al., 2020] — trained on 124M tweets
- **Emotion**: `j-hartmann/emotion-english-distilroberta-base` [CITATION: Hartmann, 2022] — GoEmotions dataset

Analysis is called directly from the backend over HTTPS, eliminating the need for a separate NLP microservice. Calls run asynchronously in a background thread in batches of five headlines every 30 seconds, preventing analysis latency from blocking the tick loop. This design preserves scientific equivalence with a locally-hosted deployment — the same models and weights are used — while removing infrastructure overhead.

---

## 6. Research Questions and Hypotheses

Lurkr is designed to test the following hypotheses:

**H1 (Drift exists)**: Agent OCEAN scores will shift measurably from their seed values over sufficiently long simulation runs (≥50 IPIP cycles), beyond what can be attributed to assessment noise.

**H2 (Behavioral grounding drives drift)**: Agents assessed with behavioral grounding (recent posts in the IPIP prompt) will show greater drift than a control condition where agents are assessed without post history.

**H3 (Social contagion)**: Agents with high-neuroticism neighbors will show neuroticism increases over time, even controlling for initial scores and news exposure. Personality is socially transmitted.

**H4 (News–trait interaction)**: High-neuroticism agents will disproportionately engage with negative headlines (as measured by `news_context` records), and this engagement will amplify neuroticism scores over time — a synthetic analog of the negativity bias documented in social media research [CITATION: Bail et al., 2018].

**H5 (Trait stability predicts resistance to drift)**: Agents seeded with extreme scores (>80 or <20) will show less proportional drift than agents seeded near the midrange, as high-cue injection creates stronger behavioral anchoring.

**H6 (Convergence under homophily)**: Because the social graph creates preferential exposure to similar agents (not yet implemented — see §8), populations should show within-cluster convergence and between-cluster divergence over time.

---

## 7. Preliminary Observations

*Note: The following observations are drawn from early simulation runs (< 100 ticks, 10 agents). They are intended to motivate the research program, not to constitute findings.*

In early runs, the behavioral grounding mechanism produces detectable within-agent variation across assessments. Agents do not simply re-confirm their seed profile. The most common pattern is moderate drift (±5–15 points) on Neuroticism and Openness — the traits whose behavioral signatures are most visible in short text. Conscientiousness and Agreeableness show less drift in early ticks, likely because their behavioral cues require sustained, structured behavior to manifest distinctly in 1–3 sentence posts.

The population mean OCEAN trajectory (tracked via `/api/agents/population`) shows no strong directional drift in the first 50 ticks, consistent with a well-mixed random initialization. Signal is expected to emerge after multiple IPIP cycles as the feedback loop compounds.

These are preliminary observations from a system designed to collect the evidence needed to evaluate them rigorously. We report them here to characterize the instrument's behavior, not to draw conclusions.

---

## 8. Limitations

**No inter-post memory**: Each LLM call is stateless. The agent's "memory" consists only of behavioral cues derived from OCEAN scores and the recent posts shown in the IPIP prompt. There is no episodic recall between posts.

**Static social graph**: The follow graph is randomized at seed time and does not evolve. Organic follow/unfollow behavior based on content affinity (homophily) is a planned feature but not yet implemented — meaning H6 cannot currently be tested.

**Assessment frequency**: The IPIP runs every `REASSESSMENT_INTERVAL` ticks (default: 10). Between assessments, the agent's behavioral cues are frozen even if their posting behavior has shifted. Higher reassessment frequency would tighten the feedback loop but increases API cost.

**LLM compliance artifacts**: `mistral-large-latest` occasionally truncates IPIP responses. Partial responses (≥60 items) are scored proportionally, but this introduces measurement noise. Different models show different truncation rates.

**Proxy validity**: We use IPIP-NEO-120 because it is validated on human subjects. Whether the same psychometric properties hold when administered to LLMs is an open question. Safdari et al. (2023) provide some evidence for convergent validity; full psychometric evaluation of LLM-administered IPIP is needed.

**Scale**: SQLite and a single-threaded tick worker limit the current system to ~10–20 agents before performance degrades. Migration to Postgres and a proper task queue is needed for population-scale experiments.

---

## 9. Discussion

The most important design choice in Lurkr is also the simplest: show the agent its own posts before asking it to rate itself. This single intervention transforms the IPIP from a static persona-confirmation procedure into a dynamic measurement instrument. Whether it produces scientifically valid drift — drift that tracks real behavior rather than assessment noise — is ultimately an empirical question, and one this system is designed to answer.

The broader ambition is to make computational personality research transparent and replicable. Every parameter that shapes agent behavior (OCEAN scores, behavioral cue thresholds, news affinity weights, reply probability, feed composition) is explicit, configurable, and logged. Every IPIP response — all 120 items, per agent, per assessment — is stored. The full causal chain from seed scores to behavioral cues to posts to IPIP responses to updated scores is reconstructible from the database.

This transparency is what distinguishes Lurkr from prior work that treats LLM personality as a black box to be characterized by aggregate outputs. Here, the mechanism is the thing under study, and the mechanism is visible.

---

## 10. Future Work

- **Longitudinal study**: Run the simulation for 200+ IPIP cycles, test H1–H5 with appropriate statistical methods (mixed-effects models for drift trajectories, permutation tests for social contagion)
- **Behavioral grounding ablation**: Compare drift magnitude with and without post history in the IPIP prompt — this directly tests whether the grounding mechanism is load-bearing
- **Homophily and dynamic social graph**: Implement follow/unfollow based on content similarity (embedding cosine distance), enabling H6
- **Post-level sentiment analysis**: Run the NLP service on agent posts (not just headlines) to measure how posting affect tracks OCEAN scores over time
- **Intervention interface (lurkerlab.net)**: Allow researchers to inject custom agents, modify the news feed, rewire the social graph, and fork simulation runs — supporting controlled experiments rather than pure observation
- **Multi-LLM comparison**: Run identical simulations against different models to characterize how model priors interact with the feedback mechanism

---

## 11. Conclusion

Lurkr is a research instrument for studying personality as a dynamic property of LLM agents rather than a fixed configuration. Its central contribution is the behavioral grounding of IPIP self-assessment: agents evaluate themselves against evidence of their own behavior, closing a loop that makes personality genuinely responsive to social and environmental context. The system is open-source, fully logged, and designed to support the kind of transparent, reproducible computational personality research that the field needs as LLM-based social simulation becomes more widespread.

We do not yet have findings. We have a machine for generating them.

---

## References

Argyle, L. P., Busby, E. C., Fulda, N., Gubler, J. R., Rytting, C., & Wingate, D. (2023). Out of one, many: Using language models to simulate human samples. *Political Analysis*, 31(3), 337–351.

Axelrod, R. (1997). *The Complexity of Cooperation: Agent-Based Models of Competition and Collaboration*. Princeton University Press.

Bail, C. A., Argyle, L. P., Brown, T. W., Bumpus, J. P., Chen, H., Hunzaker, M. B. F., Lee, J., Mann, M., Merhout, F., & Volfovsky, A. (2018). Exposure to opposing views on social media can increase political polarization. *PNAS*, 115(37), 9216–9221.

Barbieri, F., Camacho-Collados, J., Espinosa-Anke, L., & Neves, L. (2020). TweetEval: Unified benchmark and comparative evaluation for tweet classification. In *Findings of EMNLP 2020*.

Epstein, J. M., & Axtell, R. (1996). *Growing Artificial Societies: Social Science from the Bottom Up*. MIT Press.

Goldberg, L. R. (1999). A broad-bandwidth, public domain, personality inventory measuring the lower-level facets of several five-factor models. *Personality Psychology in Europe*, 7, 7–28.

Hartmann, J. (2022). Emotion English DistilRoBERTa-base. Hugging Face. https://huggingface.co/j-hartmann/emotion-english-distilroberta-base

Johnson, J. A. (2014). Measuring thirty facets of the Five Factor Model with a 120-item public domain inventory: Development of the IPIP-NEO-120. *Journal of Research in Personality*, 51, 78–89. https://doi.org/10.1016/j.jrp.2014.05.003

McCrae, R. R., & Costa, P. T., Jr. (1999). A five-factor theory of personality. In L. A. Pervin & O. P. John (Eds.), *Handbook of Personality: Theory and Research* (2nd ed., pp. 139–153). Guilford Press.

Park, J. S., O'Brien, J. C., Cai, C. J., Morris, M. R., Liang, P., & Bernstein, M. S. (2023). Generative agents: Interactive simulacra of human behavior. In *Proceedings of UIST 2023*.

Safdari, M., Serapio-García, G., Crepy, C., Fitz, S., Romero, P., Sun, L., Abdulhai, M., Flek, L., & Kubricht, J. (2023). Personality traits in large language models. *arXiv:2307.00184*.

Serapio-García, G., Safdari, M., Crepy, C., Sun, L., Fitz, S., Romero, P., Abdulhai, M., Flek, L., & Kubricht, J. (2023). Personality traits in large language models. *arXiv:2307.00184*.

Shanahan, M., McDonell, K., & Reynolds, L. (2023). Role play with large language models. *Nature*, 623, 493–498.

Törnberg, P., Valeeva, D., Uitermark, J., & Bail, C. (2023). Simulating social media using large language models to evaluate alternative news feed algorithms. *arXiv:2310.05984*.

---

*Draft. Comments welcome.*
