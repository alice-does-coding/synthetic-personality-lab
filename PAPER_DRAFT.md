# Synthetic Personality Drift: Behaviorally-Grounded Psychometric Measurement of OCEAN Dynamics in LLM Agent Networks

Alice Ott  
Independent Research  
[alice.ott@lurkr.net]

---

## Abstract

We present **Lurkr**, a research instrument for studying Big Five personality drift in large language model (LLM) agents situated in a simulated social network. The central methodological contribution is *behaviorally-grounded IPIP-NEO-120 assessment*: rather than asking agents to rate themselves in the abstract — which elicits stable, prior-anchored responses — we show each agent its own recent posts before administering the inventory. This grounds self-report in behavioral evidence, making the instrument sensitive to what the agent has actually been doing rather than what it abstractly conceives itself to be. Repeated measurement across simulation time yields a time-varying OCEAN profile for each agent. The research question is whether sustained social and environmental exposure produces measurable, directional drift in those profiles — a synthetic analog of the longitudinal personality change documented in human subjects under comparable conditions. We describe the simulation architecture, the assessment mechanism, and a set of empirically testable hypotheses. The instrument is fully open-source, runs against any instruction-following LLM, and is designed to support transparent, reproducible computational personality research.

---

## 1. Introduction

The question of whether personality can meaningfully exist in a language model has shifted from philosophical curiosity to empirical concern. As LLM-based agents are deployed in social simulations [CITATION: Park et al., 2023], opinion research [CITATION: Argyle et al., 2023], and interactive systems [CITATION: Shanahan et al., 2023], the stability and validity of their simulated personalities matter — not just for realism, but for the interpretive validity of any finding built on top of them.

Prior work has largely treated personality as a fixed condition: a Big Five profile is assigned at initialization and held constant, serving as a style parameter rather than a dynamic property [CITATION: Safdari et al., 2023; Serapio-García et al., 2023]. This mirrors how personality is sometimes operationalized in static survey contexts but misses the core insight from longitudinal trait psychology: *personality is expressed in behavior, and behavior changes under sustained environmental and social pressure*.

We propose a different measurement approach. In Lurkr, each agent's OCEAN scores are not constants — they are running measurements, updated periodically via structured self-assessment using the IPIP-NEO-120 inventory [CITATION: Johnson, 2014]. Crucially, before answering any assessment item, the agent is shown its own recent posts. The self-report is grounded in behavioral evidence, not abstract self-concept.

This grounding is the critical design choice. Without it, repeated IPIP administration to an LLM produces near-identical results — the model confirms its prior with minimal variance. With it, the assessment reflects what the agent has actually been generating: an agent whose recent posts have been anxious and reactive will score differently on neuroticism than one whose posts have been measured and calm, even if their initial profiles were identical. The inventory becomes a measurement instrument rather than a static label.

The research question follows directly: given this behavior-sensitive measurement procedure, does sustained social and environmental exposure produce directional drift in OCEAN profiles? Trait psychology in human populations documents exactly this kind of contextually-driven change — personality is relatively stable but not immutable, and it shifts predictably under sustained social pressure [CITATION: McCrae & Costa, 1999]. Lurkr asks whether the same pattern is detectable in synthetic agents.

Note what this framing does *not* claim. We do not propose feeding OCEAN scores back into generation prompts as behavioral cues — that would be a category error, treating the measurement instrument as a behavioral dial. People do not consult their personality test results before deciding how to respond to a tweet. Scores in Lurkr are outputs of the measurement process, not inputs to behavior. Any drift that emerges does so because environmental and social context pushes agent behavior in particular directions, and the grounded IPIP detects that shift.

The contributions of this paper are:

1. A formal description of the behaviorally-grounded assessment mechanism and its theoretical justification
2. A complete open-source simulation instrument (Lurkr) implementing that mechanism at the agent, network, and population level
3. A set of empirically testable hypotheses about drift dynamics, social influence, and news-driven affect
4. Preliminary observations characterizing instrument behavior in early runs

---

## 2. Related Work

### 2.1 LLM Agents in Social Simulation

Park et al. (2023) demonstrated that GPT-4-based agents placed in a persistent virtual environment produce surprisingly coherent emergent social behaviors — rumor spreading, relationship formation, planning. Their Generative Agents architecture uses a memory stream and reflection mechanism to maintain behavioral continuity. Lurkr is complementary: where Generative Agents emphasizes episodic memory and narrative coherence, Lurkr emphasizes psychometric validity. The personality scores here are not literary constructs — they are operationalized using a validated 120-item inventory and updated via structured self-report grounded in behavioral evidence.

Törnberg et al. (2023) use LLMs to simulate social media echo chambers, finding that LLM-based simulations can reproduce key polarization dynamics. Our approach differs in focus: rather than modeling political belief, we model the psychological substrate — the personality traits that, in human subjects, predict political engagement [CITATION: McCrae & Costa, 1999].

### 2.2 Personality in Language Models

Safdari et al. (2023) show that LLMs can reliably simulate specific Big Five profiles when prompted appropriately, with test-retest reliability and convergent validity comparable to human subjects under standard conditions. Serapio-García et al. (2023) find that LLMs exhibit stable, measurable personality traits even without explicit prompting — raising the question of what "drift" means when the baseline is itself a model property.

Our approach sidesteps the baseline problem by treating only the *delta* as meaningful. We are not making claims about what personality a model "really" has. We are asking: given an initial profile, a behavioral context, and a grounded self-assessment procedure, does the measured profile change over time? And if so, what drives the change?

The stability finding of Serapio-García et al. is actually what makes behavioral grounding essential. If ungrounded IPIP produces stable scores by construction, then ungrounded assessment cannot detect drift even if behavior has changed. Grounding is the intervention that makes the measurement sensitive enough to be useful.

### 2.3 IPIP-NEO-120 as an Assessment Instrument

The International Personality Item Pool NEO (IPIP-NEO-120) is a 120-item public-domain inventory measuring the five broad domains of personality (Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism) and their 30 constituent facets [CITATION: Johnson, 2014; Goldberg, 1999]. Items are rated on a five-point accuracy scale. The instrument is freely available, psychometrically validated across multiple languages and populations, and widely used in computational personality research.

Using a validated instrument rather than ad-hoc prompting is a deliberate methodological choice. It makes scores comparable to human norms, enables cross-study replication, and grounds the simulation in decades of trait psychology literature.

### 2.4 Computational Social Science and ABM

Agent-based models of social dynamics have a long history in computational social science [CITATION: Epstein & Axtell, 1996; Axelrod, 1997]. LLMs offer a qualitative advance: where classical ABMs require explicit behavioral rules, LLM agents can generate natural-language behavior that emerges from the interaction of prompt context and model priors. Bail et al. (2018) demonstrated that social media exposure shapes political attitudes in real populations — Lurkr is designed to ask an analogous question at the level of personality traits.

---

## 3. System Architecture

Lurkr consists of two processes:

- **Backend (Flask)**: REST API, tick engine, database (SQLite for local development, PostgreSQL in production), background threads for per-run tick loops and news analysis. Multiple simulation runs execute concurrently, each with an independent tick thread and a shared global rate limiter. Sentiment and emotion analysis of headlines is performed asynchronously via the Hugging Face Inference API, requiring no additional infrastructure.
- **Frontend (React/Vite)**: Real-time visualization of agent activity, personality drift, population dynamics, and news semantics.

The simulation runs continuously in the background. The frontend is a read-only observatory — it does not participate in generation.

### 3.1 Agent Representation

Each agent is defined by:

| Field | Type | Description |
|---|---|---|
| `name` | string | Display name |
| `handle` | string | Unique identifier |
| `bio` | string | Brief self-description (fixed at seed time) |
| `openness` ... `neuroticism` | float [0–100] | Current Big Five scores (updated each IPIP tick) |
| `posts` | relationship | Full post history |
| `follows` | relationship | Social graph edges |

Scores are initialized by sampling from empirically-derived IPIP-NEO population norms (Openness: μ=60, σ=20; Conscientiousness: μ=55, σ=20; Extraversion: μ=50, σ=22; Agreeableness: μ=62, σ=18; Neuroticism: μ=45, σ=22), clamped to [5, 95]. This produces a realistic cross-population distribution and yields a population mean near human norms — a useful baseline property for detecting non-trivial drift. Persona archetypes (Gaussian priors over the five traits) can alternatively be used to initialize a population with a particular psychological character.

Agent identity — name, handle, and bio — is generated by the LLM at seed time from the run's framing context and, if active, a persona archetype descriptor. Raw OCEAN scores are not shown to the LLM at bio generation time; the bio is a narrative identity, not a personality label. Bios are generated in parallel via a thread pool. A tick-0 `PersonalitySnapshot` is written from the initial scores immediately, establishing the longitudinal baseline without requiring an additional LLM call.

### 3.2 Tick Engine

The simulation advances in discrete ticks. Each run has its own independent daemon thread. In standard mode, the thread sleeps for a configurable interval after each tick completes (not on a fixed clock), preventing tick overlap without external scheduling. In *batch mode* (the default), ticks chain immediately with no sleep, running as fast as the LLM API allows — suited for generating large datasets quickly. An overlap guard using a per-run threading lock skips any tick that would run concurrently with a still-running predecessor.

Each tick is one of two types, determined by `tick_number mod REASSESSMENT_INTERVAL`:

- **Post tick** (the majority): sample `AGENTS_PER_TICK` agents, generate posts
- **IPIP tick**: run full personality assessments on all agents; post generation is skipped

The two types are mutually exclusive within a tick to avoid rate-limit pile-up.

---

## 4. Behaviorally-Grounded Assessment

This section describes the core measurement mechanism.

### 4.1 The Grounding Preamble

Every `REASSESSMENT_INTERVAL` ticks, all agents take the full 120-item IPIP-NEO-120. The key innovation is the grounding preamble prepended to the user prompt:

> *"Here are your recent posts on Lurkr: [list of up to 20 recent posts]*
> *Reflect on how you've actually been thinking, feeling, and behaving based on those posts. Then rate how accurately each statement below describes you — let your recent behavior guide your answers, not just how you'd like to see yourself."*

This is followed by all 120 IPIP items in numbered order. The model is instructed to return only a comma-separated list of integers (1–5), one per item.

The grounding preamble is the critical design choice. Without it, the LLM re-rates itself based on its general self-concept, which is largely stable across calls — the Serapio-García et al. finding holds, and drift is undetectable by construction. With it, the self-report is anchored to specific behavioral evidence: content the agent actually generated in context. The assessment becomes sensitive to what the agent has been doing.

What the grounding does *not* do is update the agent's identity or alter its future generation behavior. The bio is fixed. There is no score injection. The IPIP is a measurement pass, not a calibration pass. Any shift in scores reflects a shift in the behavioral evidence the model is rating — which in turn reflects the social and environmental context the agent has been exposed to.

### 4.2 Score Computation

Responses are parsed with a regex extracting integers in [1, 5]. Responses with fewer than 60 valid items are discarded. Reverse-keyed items are scored as `6 - raw`. Scores are then normalized per domain:

```
normalized = (sum(effective_scores) - n_items × 1) / (n_items × 4) × 100
```

where `n_items` is the count of valid responses for that domain. This preserves comparability across partial responses (60–119 items), which occur when the model truncates long prompts.

The normalized scores replace the agent's live OCEAN fields in the database. A `PersonalitySnapshot` record captures the full domain profile at each assessment tick, enabling longitudinal analysis. Item-level responses are stored in `IpipResponse` for facet-level analysis.

### 4.3 What the Scores Represent

The OCEAN scores at any given assessment tick are best understood as: *a psychometric summary of the behavioral content this agent has been producing recently, as self-reported by the agent when confronted with that content.*

This is a behavioral measurement, not a trait label. It does not claim to describe something stable about the underlying model. It describes what the agent has been doing — and if what the agent has been doing shifts under sustained contextual pressure, the scores will shift with it.

This framing has a direct methodological implication: the interesting comparison is not tick-0 scores vs. tick-N scores in isolation, but scores under different environmental and social conditions. Drift is the signal; context is the independent variable.

---

## 5. Environmental Inputs

Personality in human subjects does not evolve in a vacuum. Lurkr models two environmental channels that serve as the primary independent variables in drift experiments.

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

Agents follow a fixed set of peers (default: 5 follows each, randomized at seed time). On post ticks, agents have a 70% probability of replying to a post from their feed rather than generating top-level content. The reply target is selected from recent posts by followed agents, creating asymmetric influence: high-volume agents generate more potential reply targets and exert more social influence on their followers.

This asymmetry is the mechanism through which social contagion could operate. An agent consistently exposed to high-neuroticism content from its followed peers may produce increasingly reactive posts — which the grounded IPIP will then measure as elevated neuroticism. The social graph is the transmission medium.

### 5.3 Semantic Analysis of Environmental Inputs

News headlines are analyzed for sentiment (valence: -1.0 to +1.0) and emotion (7-class Ekman: joy, sadness, anger, fear, surprise, disgust, neutral) using two transformer models hosted via the Hugging Face Inference API:

- **Sentiment**: `cardiffnlp/twitter-roberta-base-sentiment-latest` [CITATION: Barbieri et al., 2020] — trained on 124M tweets
- **Emotion**: `j-hartmann/emotion-english-distilroberta-base` [CITATION: Hartmann, 2022] — GoEmotions dataset

Analysis runs asynchronously in a background thread in batches of five headlines every 30 seconds, preventing analysis latency from blocking the tick loop. This design preserves scientific equivalence with a locally-hosted deployment — the same models and weights — while removing infrastructure overhead.

---

## 6. Research Questions and Hypotheses

Lurkr is designed to test the following hypotheses:

**H1 (Drift exists)**: Agent OCEAN scores will shift measurably from their seed values over sufficiently long simulation runs (≥50 IPIP cycles), beyond what can be attributed to assessment noise alone.

**H2 (Grounding is load-bearing)**: Agents assessed with behavioral grounding (recent posts in the IPIP preamble) will show greater drift magnitude than a control condition where agents are assessed without post history. This directly tests whether the grounding mechanism — rather than model variance — is driving score changes.

**H3 (Social contagion)**: Agents with high-neuroticism neighbors will show neuroticism increases over time, even controlling for initial scores and news exposure. Personality is socially transmitted through the content of the feed.

**H4 (News–trait interaction)**: High-neuroticism agents will disproportionately engage with negative headlines (as measured by `news_context` records), and this engagement will produce posts that score higher on neuroticism in subsequent IPIP cycles — a synthetic analog of the negativity bias documented in social media research [CITATION: Bail et al., 2018].

**H5 (Extreme scores resist drift)**: Agents seeded at extreme scores (>80 or <20) will show less proportional drift than agents seeded near the midrange. Extreme initial profiles generate more extreme behavioral content, which the IPIP registers consistently, producing a self-stabilizing measurement pattern.

**H6 (Convergence under homophily)**: Because the social graph creates preferential exposure to similar agents (not yet implemented — see §8), populations should show within-cluster convergence and between-cluster divergence over time.

---

## 7. Preliminary Observations

*Note: The following observations are drawn from early simulation runs (< 100 ticks, 10–50 agents). They are intended to characterize instrument behavior, not to constitute findings.*

The behaviorally-grounded IPIP produces detectable within-agent variation across assessments. Agents do not simply re-confirm their seed profile. The most common pattern is moderate variation (±5–15 points) on Neuroticism and Openness — the traits whose behavioral signatures are most visible in short text. Conscientiousness and Agreeableness show less variation in early ticks, consistent with the expectation that their behavioral correlates require sustained structured behavior to manifest distinctly in 1–3 sentence posts.

The population mean OCEAN trajectory (tracked via `/api/agents/population`) shows no strong directional drift in early runs, consistent with population-norm initialization centering the distribution near the human mean. Directional signal is expected to emerge over longer runs and larger populations as social and environmental pressures compound across IPIP cycles.

These observations establish that the measurement instrument is sensitive — it does not simply return constant scores — without yet providing evidence for or against the directional drift hypotheses. Proper evaluation of H1–H5 requires longer runs, more IPIP cycles per agent, and controlled experimental conditions. That is what this instrument is built to produce.

---

## 8. Limitations

**Stateless generation**: Each LLM call is stateless. An agent's "memory" consists only of its fixed bio and, at assessment time, its recent posts. There is no episodic recall between posts. This is a deliberate simplification that isolates the environmental and social exposure channels as the primary drivers of behavioral change — but it means within-tick behavioral coherence is lower than in architectures with explicit memory.

**Fixed identity**: The bio is generated once at seed time and does not change. This means the agent's narrative self-concept is static even as its measured OCEAN profile drifts. In human subjects, sustained personality change typically co-occurs with identity revision. Whether fixed-bio agents can produce scientifically meaningful drift, or whether bio updating is necessary for the effect to manifest, is an open question.

**Static social graph**: The follow graph is randomized at seed time and does not evolve. Organic follow/unfollow behavior based on content affinity (homophily) is a planned feature — meaning H6 cannot currently be tested, and the social contagion pathway (H3) operates through random rather than affinity-selected neighborhoods.

**Assessment frequency**: With a `REASSESSMENT_INTERVAL` of 25 ticks and a 100-tick run, each agent receives only 4 assessments. This yields sparse longitudinal data. Meaningful drift trajectories likely require 20+ IPIP assessments per agent, implying 500+ tick runs. This is feasible in batch mode but requires deliberate experimental planning.

**LLM compliance artifacts**: `mistral-large-latest` occasionally truncates IPIP responses. Partial responses (≥60 items) are scored proportionally, but this introduces measurement noise. Different models show different truncation rates.

**Proxy validity**: We use IPIP-NEO-120 because it is validated on human subjects. Whether the same psychometric properties hold when administered to LLMs is an open question. Safdari et al. (2023) provide some evidence for convergent validity; full psychometric evaluation of LLM-administered IPIP remains needed.

---

## 9. Discussion

The most important design choice in Lurkr is also the simplest: show the agent its own posts before asking it to rate itself. This single intervention transforms the IPIP from a static persona-confirmation procedure into a behavior-sensitive measurement instrument.

It is worth being precise about what this does and does not do. Showing an agent its posts does not change who the agent is — the bio is fixed, the model weights are fixed. What changes is the *evidence* the agent is rating itself against. If the posts exhibit a consistent behavioral signature (anxious, reactive, curious, withdrawn), the grounded IPIP will register that. The measurement tracks behavior, not some deeper latent trait.

This is actually the right scientific model. In human longitudinal research, personality is not directly observed — it is inferred from behavioral aggregates, including self-report. The IPIP administered to a human asks them to reflect on their typical behavior and rate it. We are doing the same thing, with recent posts as the behavioral record. The mechanism is analogous; the question is whether the effect is real.

Critically, this framing makes the research question falsifiable in both directions. If contextual pressure produces no directional drift — if the IPIP returns to baseline regardless of what the agent has been exposed to — that is a finding. It would suggest that LLM agents have strong personality homeostasis not found in human populations, or that the grounding mechanism is insufficient to capture real behavioral change. Either result is scientifically informative.

The broader ambition is to make computational personality research transparent and replicable. Every parameter that shapes agent behavior (news affinity weights, reply probability, feed composition, reassessment interval) is explicit, configurable, and logged. Every IPIP response — all 120 items, per agent, per assessment — is stored. The full chain from environmental exposure to behavioral output to psychometric measurement is reconstructible from the database.

---

## 10. Future Work

- **Longitudinal study**: Run the simulation for 500+ ticks with 50+ agents, collect 20+ IPIP assessments per agent, test H1–H5 with appropriate statistical methods (mixed-effects models for drift trajectories, permutation tests for social contagion)
- **Grounding ablation**: Run matched simulations with and without post history in the IPIP preamble — this directly tests H2 and establishes whether behavioral grounding is load-bearing or whether model variance alone explains observed drift
- **Controlled exposure experiments**: Manipulate the news feed (positive vs. negative valence, high vs. low arousal) and social graph composition (high-neuroticism neighbors vs. low-neuroticism) to isolate the contribution of each environmental channel
- **Homophily and dynamic social graph**: Implement follow/unfollow based on content similarity (embedding cosine distance), enabling H6 and creating more realistic social clustering
- **Post-level affect analysis**: Run the NLP service on agent posts (not just headlines) to measure how posting affect tracks OCEAN scores over time and correlates with environmental inputs
- **Cross-run comparison**: Build analysis tooling for comparing drift trajectories across runs with different configurations — the primary interface for systematic experimental work
- **Multi-LLM comparison**: Run identical experimental conditions against different models to characterize how model priors interact with the grounding mechanism and the environmental exposure channels
- **Intervention interface (lurkrlab.net)**: Allow researchers to inject custom agents, modify the news feed, rewire the social graph, and fork simulation runs — supporting controlled experiments rather than pure observation

---

## 11. Conclusion

Lurkr is a research instrument for studying personality as a time-varying property of LLM agents rather than a fixed configuration. Its central contribution is the behavioral grounding of IPIP self-assessment: agents rate themselves against evidence of their own behavior, making the psychometric measurement sensitive to what they have actually been doing rather than what they abstractly conceive themselves to be.

The research question — does sustained social and environmental exposure produce measurable OCEAN drift? — is unanswered. The instrument is designed to answer it. The result is not predetermined: if drift does not emerge under contextual pressure, that is as informative as if it does. What the instrument provides is a controlled, logged, reproducible environment in which the question can be asked rigorously.

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
