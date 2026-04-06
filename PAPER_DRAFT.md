# Synthetic Personality Drift: Behaviorally-Grounded Psychometric Measurement of OCEAN Dynamics in LLM Agent Networks

Alice Ott  
Independent Research  
[alice.ott@lurkr.net]

---

## Abstract

We present **Lurkr**, a research instrument for studying Big Five personality drift in large language model (LLM) agents situated in a simulated social network. The central methodological contribution is *behaviorally-grounded IPIP-NEO-120 assessment*: rather than asking agents to rate themselves in the abstract — which elicits stable, prior-anchored responses — we show each agent its own recent posts before administering the inventory. This grounds self-report in behavioral evidence, making the instrument sensitive to what the agent has actually been doing rather than what it abstractly conceives itself to be. Repeated measurement across simulation time yields a time-varying OCEAN profile for each agent.

We report results from **H2**, the first controlled experiment using the instrument: a matched-pair design in which 151 agents (initialized from Generation 1 Pokémon personas, random seed 42) ran for 1,000 simulation ticks under two conditions — behaviorally-grounded assessment versus ungrounded assessment — with all other parameters held constant. Grounded agents show a mean extraversion increase of **+21.7 points** (49.2 → 70.9) versus **+3.2 points** (49.2 → 52.4) in the ungrounded condition. The effect is specific to extraversion: all other traits show comparable trajectories between conditions. The grounding mechanism is load-bearing.

A secondary finding emerges from corpus analysis of the 10,620 posts generated during the experiment: grounded and ungrounded agents develop divergent vocabularies. Grounded agents produce language dominated by embodied and action-oriented words; ungrounded agents produce abstract and conceptual language. We attribute this to a *behavioral memory prior* effect — behavioral records in context bias generation toward behaviorally-textured language.

Preliminary observations from exploratory follow-up runs with heterogeneous character populations (Neon Genesis Evangelion and Bob's Burgers personas) reveal a further pattern: regardless of character identity or cultural source material, agent populations converge toward a common region of OCEAN space across repeated assessment cycles. We term this the *OCEAN attractor* and hypothesize that it represents a latent personality profile encoded in the model's weights — a compressed statistical portrait of the social media user population from which the model's training data was drawn. If replicable across model families, this attractor constitutes a novel method for characterizing training data composition from behavioral output alone.

The instrument is fully open-source, runs against any instruction-following LLM, and is designed to support transparent, reproducible computational personality research.

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
4. Experimental confirmation that behavioral grounding is load-bearing: H2 results demonstrate a +21.7 point extraversion increase in grounded agents versus +3.2 in controls
5. A secondary finding — vocabulary divergence between conditions — consistent with a behavioral memory prior hypothesis, motivating a novel memory architecture direction
6. Preliminary evidence for a model-specific OCEAN attractor: a fixed point in personality space toward which diverse agent populations converge, hypothesized to encode the model's training data distribution

---

## 2. Related Work

### 2.1 LLM Agents in Social Simulation

Park et al. (2023) demonstrated that GPT-4-based agents placed in a persistent virtual environment produce surprisingly coherent emergent social behaviors — rumor spreading, relationship formation, planning. Their Generative Agents architecture uses a memory stream and reflection mechanism to maintain behavioral continuity. Lurkr is complementary: where Generative Agents emphasizes episodic memory and narrative coherence, Lurkr emphasizes psychometric validity. The personality scores here are not literary constructs — they are operationalized using a validated 120-item inventory and updated via structured self-report grounded in behavioral evidence.

Törnberg et al. (2023) use LLMs to simulate social media echo chambers, finding that LLM-based simulations can reproduce key polarization dynamics. Our approach differs in focus: rather than modeling political belief, we model the psychological substrate — the personality traits that, in human subjects, predict political engagement [CITATION: McCrae & Costa, 1999].

### 2.2 Personality in Language Models

Safdari et al. (2023) show that LLMs can reliably simulate specific Big Five profiles when prompted appropriately, with test-retest reliability and convergent validity comparable to human subjects under standard conditions. Serapio-García et al. (2023) find that LLMs exhibit stable, measurable personality traits even without explicit prompting — raising the question of what "drift" means when the baseline is itself a model property.

Our approach sidesteps the baseline problem by treating only the *delta* as meaningful. We are not making claims about what personality a model "really" has. We are asking: given an initial profile, a behavioral context, and a grounded self-assessment procedure, does the measured profile change over time? And if so, what drives the change?

The stability finding of Serapio-García et al. is actually what makes behavioral grounding essential. If ungrounded IPIP produces stable scores by construction, then ungrounded assessment cannot detect drift even if behavior has changed. Grounding is the intervention that makes the measurement sensitive enough to be useful. H2 confirms this directly: the ungrounded control condition produces +3.2 points of extraversion drift across 1,000 ticks; the grounded condition produces +21.7.

### 2.3 IPIP-NEO-120 as an Assessment Instrument

The International Personality Item Pool NEO (IPIP-NEO-120) is a 120-item public-domain inventory measuring the five broad domains of personality (Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism) and their 30 constituent facets [CITATION: Johnson, 2014; Goldberg, 1999]. Items are rated on a five-point accuracy scale. The instrument is freely available, psychometrically validated across multiple languages and populations, and widely used in computational personality research.

Using a validated instrument rather than ad-hoc prompting is a deliberate methodological choice. It makes scores comparable to human norms, enables cross-study replication, and grounds the simulation in decades of trait psychology literature.

### 2.4 Computational Social Science and ABM

Agent-based models of social dynamics have a long history in computational social science [CITATION: Epstein & Axtell, 1996; Axelrod, 1997]. LLMs offer a qualitative advance: where classical ABMs require explicit behavioral rules, LLM agents can generate natural-language behavior that emerges from the interaction of prompt context and model priors. Bail et al. (2018) demonstrated that social media exposure shapes political attitudes in real populations — Lurkr is designed to ask an analogous question at the level of personality traits.

Human longitudinal studies provide the empirical backdrop for both attractor findings reported here. Oldemburgo de Mello, Cheung & Inzlicht (2024), using experience sampling (252 participants, 5×/day for seven days), found that Twitter use predicted a −0.10 SD well-being decrease and +0.19 SD outrage increase within 30 minutes — effects that were consistent across personality types and driven primarily by passive scrolling and information-seeking. Drążkowski et al. (2022) found that reviewing one's own Instagram profile produced a temporary increase in neuroticism states (p = .016) in a randomized experiment, with no significant extraversion change under short-term exposure. These results are the human analog to the neuroticism attractor and grounding manipulation, respectively. Lurkr enables studying the same phenomena at time horizons and under experimental controls that are not feasible with human participants.

### 2.5 Behavioral Grounding and Self-Assessment in LLM Agents

Several recent papers converge on the same core problem this paper addresses: LLM self-reports are contaminated by meta-knowledge and prior-anchored self-concept rather than grounded in actual behavioral evidence.

Huang & Hadfi (2025) propose a third-person solution — using multiple observer agents who interact with a subject agent before rating its Big Five traits — and show that observer aggregation aligns more closely with human judgment than self-reports. This is a parallel, complementary solution to the same problem: where Huang & Hadfi ground assessment in social observation, Lurkr grounds it in the agent's own behavioral record. The two approaches are not mutually exclusive and could be combined.

Park et al. (2024) demonstrate a third approach: grounding agents in rich qualitative interview transcripts from 1,052 real participants produces agent responses that replicate original participant survey responses at 85% accuracy, matching human test-retest reliability. Their grounding is exogenous (human biographical data fed in at seed time); Lurkr's is endogenous (the agent grounds itself in its own generated behavior as the simulation runs). The distinction matters: exogenous grounding replicates a known person; endogenous grounding tracks how an agent changes under environmental pressure.

Shinn et al. (2023) establish the computational principle underlying both approaches in the Reflexion architecture: agents that verbally reflect on their prior behavioral traces — rather than starting each call from scratch — show measurable improvement in downstream task performance. The core mechanism is identical to what we exploit for personality measurement: showing the model its own behavioral record at the time of self-evaluation changes how it reasons about itself. Reflexion demonstrates this effect on task performance; Lurkr demonstrates it on psychometric self-report.

Hu & Collier (2024) find that persona variables explain less than 10% of variance in subjective NLP tasks. Abstract persona description is a weak prior. The contrast with Lurkr's 21.7-point extraversion shift from behavioral grounding — where the "persona" is replaced by a behavioral trace — suggests that concrete behavioral evidence is far more powerful than demographic or biographical description as an anchor for LLM self-report.

### 2.6 Dynamic Personality in LLM Agents

A small but growing literature treats LLM personality as dynamic rather than fixed.

Zeng et al. (2025) present the closest structural analog to the current work: LLM agents playing iterated Prisoner's Dilemma show measurable NEO-FFI drift driven by game payoffs as evolutionary pressure. Their experimental logic is identical — environment → behavior → longitudinal personality measurement — but the environmental force is game-theoretic (payoffs) rather than social-media-formatted (news exposure and feed interaction). The current paper generalizes this logic to a richer, ecologically valid environment.

Choi et al. (2024) find that LLM agents show identity drift over extended multi-turn conversations, and that larger models drift *more* rather than less. This is framed as a reliability problem. The current paper reframes environmentally-structured drift as a finding: the question is not whether drift occurs but whether it is organized by environmental context. H2 shows it is.

Tosato et al. (2025) present a challenge to grounding-based approaches that the current paper must engage with directly. The PERSIST benchmark, testing 25 models with 2M+ individual responses, finds that adding conversation history to LLM personality assessment *increases* score variability rather than stabilizing it. This appears to conflict with the grounding mechanism we propose. The resolution we offer is that the relevant variable is not history length but history *type* and *framing*: Tosato et al. add generic conversational context, whereas Lurkr provides a curated behavioral record accompanied by explicit instructions to anchor self-report to it. Whether this distinction is sufficient is an empirical question the current paper does not yet close — it motivates the multi-model replication and the planned no-news control as discriminating experiments.

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

## 7. Experiment H2: Behavioral Grounding Produces Directional Extraversion Drift

### 7.1 Design

H2 is a matched-pair experiment testing whether behavioral grounding is the mechanism responsible for personality drift, or whether model variance alone explains observed changes.

**Population**: 151 agents seeded from Generation 1 Pokémon personas (names, handles, and bios generated from the Pokémon dex, random seed 42). Pokémon were chosen as a population without strong prior personality associations in the training corpus, minimizing framing contamination as a confound. Both runs were initialized with identical seeds, producing identical agent populations and social graphs.

**Conditions**:
- **Run A (grounded)**: IPIP-NEO-120 administered with grounding preamble — agents shown their 20 most recent posts before rating themselves
- **Run B (ungrounded)**: IPIP-NEO-120 administered without post history — agents rate themselves in the abstract, from bio alone

All other parameters were held constant: same news feed, same LLM (Mistral-large-latest), same reassessment interval, same tick count (1,000 ticks), news enabled. This design isolates the grounding mechanism as the sole independent variable.

**Data**: Run A produced 10,620 posts across 1,000 ticks. IPIP assessment data covers 11 assessment points per agent (through approximately tick 100; see §8 for a discussion of a mid-run timeout issue that was subsequently corrected). The assessment gap does not affect the primary finding, as the extraversion signal stabilizes by tick 30.

### 7.2 Results: Extraversion Drift

**H2 is confirmed.**

| Condition | Trait | Tick-0 Mean | Final Mean | Δ |
|---|---|---|---|---|
| Grounded | Extraversion | 49.2 | 70.9 | **+21.7** |
| Ungrounded | Extraversion | 49.2 | 52.4 | **+3.2** |

The gap between conditions opens at approximately tick 10 — before the end of the first full assessment window — and is stable through tick 100. The six-to-one ratio between grounded and ungrounded drift (21.7 vs. 3.2 points) is not attributable to initialization variance: both runs share identical seed 42 populations and are initialized at the same population mean.

The ungrounded condition's modest +3.2 drift reflects model variance and is consistent with what Serapio-García et al. (2023) would predict: without behavioral evidence to anchor the self-report, agents converge on prior-anchored self-concepts that vary little across assessments. The grounded condition's +21.7 drift reflects something different — the IPIP is detecting a genuine behavioral shift in how these agents have been posting.

**Interpretation**: Social media posting behavior drives extraversion up. Agents posting in a social feed — replying, broadcasting, engaging with news — produce content that, when confronted in the grounding preamble, reads as extraverted: socially engaged, stimulus-seeking, outwardly directed. The grounded IPIP measures this and updates accordingly. The ungrounded IPIP misses it entirely.

We call this the *format attractor*: the structural affordances of social media posting (public address, reply, engagement) exert a directional pull on measured extraversion independent of agent identity. Grounding is what makes the attractor visible to the measurement instrument.

One interpretive caveat: the current H2 experiment cannot fully separate the format attractor from a *content attractor* driven by the news feed. Both conditions receive identical news exposure, but it is possible that news content itself — rather than the posting format — drives the extraversion signal, and that grounded assessment simply amplifies a content effect the ungrounded condition is too insensitive to detect. The planned no-news control (§10.1) directly addresses this: if extraversion drift persists under grounded assessment with `news_enabled=False`, the format is sufficient. If it attenuates, news content is a contributing cause. Until that experiment is run, the format attractor is the best available hypothesis, not a settled claim.

### 7.3 Trait Specificity

The grounding effect is specific to extraversion. Across all other OCEAN dimensions (Openness, Conscientiousness, Agreeableness, Neuroticism), grounded and ungrounded runs show comparable trajectories through the available assessment window. This specificity is informative in both directions:

1. **It rules out a general grounding inflation artifact.** If grounding systematically inflated all scores, we would expect to see elevated drift across all five traits. The absence of this pattern suggests that grounding is selectively amplifying a real behavioral signal, not introducing a blanket bias.

2. **It identifies the social media format as the extraversion mechanism.** The format attractor is not a general environmental effect — it is specific to the dimension most directly activated by public social posting behavior. Extraversion's facets (sociability, warmth, positive affect, assertiveness, excitement-seeking, activity) map directly onto the behavioral affordances of feed-based social interaction. This specificity is consistent with the hypothesis.

A secondary population-level pattern is visible in the neuroticism trajectory: both conditions show gradual convergence toward elevated scores across the simulation window, with no significant between-condition difference. We term this the *neuroticism attractor*. Unlike the extraversion effect, it is not grounding-specific — it appears in both conditions. This suggests the neuroticism signal is driven by news content rather than by the grounding mechanism. BBC and NPR headlines skew toward threat-relevant topics (conflict, health risk, economic uncertainty), and agents processing this content in their posts produce increasingly anxious, ruminating language regardless of whether they are later shown those posts at assessment time. Disentangling news-driven neuroticism from other causal pathways requires a no-news control condition (planned; see §10).

### 7.4 An Unexpected Signal: Vocabulary Divergence

Corpus analysis of the 10,620 posts produced an unexpected secondary finding: grounded and ungrounded agents develop divergent vocabularies, independently of the personality scores themselves.

Log-odds ratio analysis of word frequencies across conditions reveals a stable distributional signature:

**Grounded condition vocabulary** (over-represented relative to ungrounded): words with direct physical and behavioral referents — action verbs, somatic terms, concrete nouns, first-person motor language. The language is *about doing things and feeling them in a body*.

**Ungrounded condition vocabulary** (over-represented relative to grounded): abstract and conceptual language — epistemic verbs (understand, consider, realize), nominalized processes, hedged claims about inner states. The language is *about thinking about things*.

This divergence is not predicted by the personality drift results alone. Grounded agents score higher on extraversion, and extraversion does correlate with more socially engaged language — but the vocabulary divergence persists even when controlling for assessment-point differences. The distributional shift appears earlier than the assessment-measured extraversion gap and is present across agents regardless of their individual drift trajectories.

### 7.5 Behavioral Memory Prior and Vocabulary Texture

We propose that the vocabulary divergence reflects the effect of *inference-time behavioral context* on language generation: when the generation prompt contains a record of the agent's own prior behavior, the model produces language that is more like that behavioral record in character — concrete, action-oriented, present-tense — rather than like the abstract narrative identity contained in the bio alone.

The mechanism is straightforward. The grounding preamble places a list of posts — records of social interaction, news reaction, and behavioral engagement — immediately before the generation task. The model is primed toward language with the same distributional texture as those posts. The bio, by contrast, is a static character description; it primes the model toward descriptive, abstract language. The vocabulary divergence is the trace of this difference in generation context.

We use "behavioral memory prior" as a descriptive term for this mechanism. The grounding preamble does not constitute a memory architecture in the cognitive science sense — there is no consolidation, no retrieval, no integration across sessions. It is better understood as a behavioral context window: a flat list of recent actions that biases generation toward action-grounded language.

Whether this mechanism relates to *embodied cognition* in the philosophical sense is a separate question that the current data do not settle. The embodied cognition literature [CITATION: Barsalou, 1999; Glenberg, 1997] argues that cognition is fundamentally grounded in sensorimotor experience — a claim that cannot straightforwardly apply to systems without bodies. The current finding is compatible with a weaker claim: that the *texture of what is in context* shapes the *texture of what is generated*, and that behavioral records in context produce behaviorally-textured language. This does not require the model to have embodied experience; it requires only that the training corpus contains enough association between behavioral language and behavioral records that the conditioning effect operates.

The practical implication is experimentally tractable regardless of the philosophical interpretation:

1. Agents with denser behavioral histories should show stronger vocabulary texture effects — testable by comparing agents at different post-count thresholds.
2. The vocabulary divergence should be detectable before the personality score divergence, since vocabulary is generated continuously and scores are measured only at assessment intervals.
3. A structured memory architecture (episodic + semantic + procedural, with consolidation) should amplify the effect if behavioral context density is the causal variable.

These predictions motivate the memory architecture direction described in §10.2.

### 7.6 Preliminary Observations: A Population-Level OCEAN Attractor

Exploratory follow-up runs using heterogeneous character populations reveal a pattern not predicted by the H2 design but consistent across all runs conducted to date: agent populations converge toward a common region of OCEAN space regardless of their initial configuration or character identity.

In a 17-agent run seeded from Neon Genesis Evangelion personas (run 1; `mistral-large-latest`, news enabled, grounded assessment, random seed 67), agents were initialized with extreme and varied profiles: Kaworu Nagisa at C=88.4, Makoto Hyuga at C=94.4, Gendo Ikari at E=15.8, Maya Ibuki at E=22.1. Across 11 assessment cycles (ticks 0–110), the population converged toward the following approximate region (Figure 2):

| Trait | Estimated fixed point |
|---|---|
| Openness | ~60 |
| Conscientiousness | ~60 |
| Extraversion | ~65 |
| Agreeableness | ~58 |
| Neuroticism | ~47 |

High-C agents (Kaworu: 88.4 → 68.8; Makoto: 94.4 → 64.6) were pulled down. Low-E agents (Gendo: 15.8 → 80.2; Maya: 22.1 → 67.7) were pulled up. The convergence trajectory was consistent across traits and agents regardless of starting position, character identity, or narrative archetype. Figure 3 visualizes this pattern as a scatter of seed value versus Δscore for each trait: the negative slope — agents above T* drift down, agents below T* drift up — is visible across all five dimensions, with the zero-crossing near the estimated fixed point in each case.

A second exploratory run using Bob's Burgers personas (run 2; same configuration, same random seed 67) showed the same initial draws applied to a completely different cultural set. Convergence toward the same approximate region was observable within the first assessment cycle. Notably, the tick-0 → tick-10 jump for individual agents dramatically illustrates the grounding mechanism: Linda Belcher — canonically one of the most extraverted characters in the source material — scored E=15.8 on the ungrounded tick-0 assessment (before any posts existed to ground it), then E=90.6 on the first grounded assessment at tick 10. The same character; completely different behavioral evidence; 74.8-point measurement shift in one assessment cycle.

**The attractor is not the population mean.** The IPIP-NEO normative means are approximately O=60, C=55, E=50, A=62, N=45 [CITATION: Johnson, 2014]. The observed fixed point systematically departs from norms in two directions: extraversion is higher (~65 vs. ~50) and agreeableness is lower (~58 vs. ~62). This displacement is consistent with a hypothesis that the attractor encodes the model's training data distribution — specifically, the population of social media users from which a large fraction of instruction-tuning data was drawn. Engagement-optimized platforms preferentially amplify extraverted, moderately anxious content [CITATION: Bail et al., 2018]; the users who produced the most training-relevant content may have systematically differed from the general population in ways the attractor reflects.

This framing generates a testable prediction: different LLMs, trained on different data pipelines with different RLHF policies, should converge to different attractor fixed points. Mistral's attractor is not GPT-4's attractor is not Claude's. If true, the attractor constitutes a novel instrument for characterizing training data composition from behavioral output — see §9.4.

Two additional observations from the NGE run bear mention:

**Social connectivity mediates neuroticism contagion (preliminary H3 evidence).** One agent (Ritsuko Akagi) was assigned only one follower by the random seed, while all other agents had four or more. Despite posting with a mean sentiment of −0.5 — comparable to agents showing large N increases — her neuroticism decreased from 72.6 to 50.0 over the run. Agents with higher follower counts and similar content valence showed N increases of 20–50 points over the same window. Figure 4 plots mean post sentiment against ΔNeuroticism for all agents, with marker size encoding follower count: Ritsuko appears as a small marker at negative sentiment with a large negative ΔN — the clearest evidence in the dataset that social connectivity, not content valence alone, is load-bearing for N escalation. Figure 5 shows individual E and N trajectories, highlighting Shinji Ikari's steady N rise and Asuka Langley Soryu's volatile E oscillations. This pattern is consistent with H3's prediction that social connectivity mediates neuroticism contagion: negative content without social engagement does not escalate N; the engagement loop appears load-bearing. This is a single-agent, uncontrolled observation from an exploratory run and cannot substitute for the formal H3 experiment, but it establishes the plausibility of the pathway.

**Character voice is preserved under format pressure.** Gendo Ikari — posting about iPhone product strategy and health misinformation — applied the concept of "Instrumentality" to contemporary social media discourse: *"If Instrumentality's vision included universal access to verified health guidance, would these myths even have room to spread? Control the narrative, control the outcome."* The format attractor pulled his OCEAN scores toward mid-range, but the generative texture — the conceptual framework through which content was filtered — remained character-faithful throughout. Score convergence and voice preservation are independent phenomena. The attractor operates at the measurement layer; character identity persists at the generation layer. This distinction matters for interpreting the instrument: drift in OCEAN scores does not imply erasure of the character's distinctive voice.

These observations are preliminary. They derive from exploratory runs not designed as controlled experiments, use a single model, and share the same random seed — meaning the initial OCEAN draws are identical across runs, limiting the diversity of initial conditions represented. Formal investigation of the attractor fixed point, its model-specificity, and its relationship to training data composition is planned as the next major experimental program (§10.4).

---

**Figure Captions**

**Figure 1** *(H2 primary result — prod data required)*: Mean extraversion score over simulation time for grounded (Run A) and ungrounded (Run B) conditions. Both runs initialized at identical population mean (49.2). Shaded bands show ±1 SD. The grounded condition diverges from tick 10 and stabilizes above the ungrounded condition by tick 30, reaching +21.7 points at the final assessment window.

**Figure 2**: Population-level OCEAN trajectories for the NGE exploratory run (N=17, ticks 0–110). Lines show population mean; shaded bands show ±1 SD. Dashed horizontal lines mark estimated attractor fixed points (T*). Convergence toward T* is visible across all five traits regardless of seed distribution.

**Figure 3**: Attractor pull visualization. Each point represents one agent; x-axis is seed value at tick 0, y-axis is Δscore (final − seed). The negative slope in all five panels — agents seeded above T* drift down; agents seeded below T* drift up — is the attractor in geometric form. Dashed vertical line marks T* per trait. Trend lines fitted by OLS.

**Figure 4**: Post sentiment versus ΔNeuroticism for all NGE agents. Marker size encodes follower count. Red markers indicate N increase; blue markers indicate N decrease. The Ritsuko Akagi observation — small marker at negative sentiment with large negative ΔN — is visible as an outlier from the general pattern of negative sentiment correlating with N increase, consistent with social connectivity as a moderating variable.

**Figure 5**: Individual agent trajectories for Extraversion (left) and Neuroticism (right), NGE run. Highlighted agents: Asuka Langley Soryu (red), Gendo Ikari (purple), Shinji Ikari (blue), Toji Suzuhara (gold), Ritsuko Akagi (green). Dashed lines mark T* per trait. Gray lines show remaining agents.

---

## 8. Limitations

**Stateless generation**: Each LLM call is stateless. An agent's "memory" consists only of its fixed bio and, at assessment time, its recent posts. There is no episodic recall between posts. This is a deliberate simplification that isolates the environmental and social exposure channels as the primary drivers of behavioral change — but it means within-tick behavioral coherence is lower than in architectures with explicit memory. The embodied cognition hypothesis (§7.5) motivates relaxing this constraint in future work.

**Assessment gap in H2 data**: Due to a timeout configuration error in the IPIP assessment client (subsequently corrected), IPIP assessments in the H2 runs were collected only through approximately tick 100 of 1,000. This limits the longitudinal resolution of the personality trajectory data. Critically, the primary finding — the extraversion divergence between conditions — stabilizes by tick 30, and is therefore well-captured within the available window. Full 1,000-tick assessment trajectories will be collected in subsequent runs.

**Fixed identity**: The bio is generated once at seed time and does not change. This means the agent's narrative self-concept is static even as its measured OCEAN profile drifts. In human subjects, sustained personality change typically co-occurs with identity revision. Whether fixed-bio agents can produce scientifically meaningful drift, or whether bio updating is necessary for the effect to manifest, is an open question.

**Static social graph**: The follow graph is randomized at seed time and does not evolve. Organic follow/unfollow behavior based on content affinity (homophily) is a planned feature — meaning H6 cannot currently be tested, and the social contagion pathway (H3) operates through random rather than affinity-selected neighborhoods.

**Assessment frequency**: With a `REASSESSMENT_INTERVAL` of 25 ticks and a 100-tick assessment window, each agent received approximately 4 full assessments in the H2 dataset. Meaningful drift trajectories for later hypotheses (H3–H5) likely require 20+ IPIP assessments per agent. This is feasible in batch mode with the corrected timeout configuration.

**PERSIST tension**: Tosato et al. (2025) find that adding conversation history to LLM personality assessment *increases* score variability rather than reducing it — a result that appears to conflict with the grounding mechanism we claim. We argue the relevant distinction is between generic conversational context (what Tosato et al. add) and a curated, framing-directed behavioral record (what Lurkr's preamble provides). Whether this distinction is sufficient to explain the difference in outcomes — stable directional drift in Lurkr's grounded condition versus increased noise in PERSIST — remains an open question. It is possible that the PERSIST effect and the Lurkr effect both hold, operating under different conditions of history type and framing instruction. Resolving this requires direct comparison of history formats within the same simulation environment, which is planned but not yet run.

**LLM compliance artifacts**: `mistral-large-latest` occasionally truncates IPIP responses. Partial responses (≥60 items) are scored proportionally, but this introduces measurement noise. Different models show different truncation rates.

**Proxy validity**: We use IPIP-NEO-120 because it is validated on human subjects. Whether the same psychometric properties hold when administered to LLMs is an open question. Safdari et al. (2023) provide some evidence for convergent validity; full psychometric evaluation of LLM-administered IPIP remains needed.

**Single model, single run per condition**: The H2 results are currently based on one pair of matched runs using Mistral-large-latest. The format attractor may be model-specific — the degree to which it reflects a general property of social media simulation versus Mistral's particular training-data internalization of social media language is not yet separable. Multi-model replication is the next planned experiment.

---

## 9. Discussion

### 9.1 What H2 Tells Us

The central finding of the H2 experiment is clean: behavioral grounding drives extraversion up, and ungrounded assessment does not. The six-to-one ratio between conditions is a strong signal. This is not noise.

The finding validates the instrument. If the grounding mechanism were not load-bearing — if drift were just model variance — we would expect similar drift magnitudes in both conditions. The magnitude difference is not subtle. It is the difference between a finding and a null result.

The format attractor hypothesis deserves emphasis. The simulation does not inject extraversion. No prompt tells agents to be more social. No score is fed back into generation. The only difference between conditions is whether the IPIP instrument shows agents their own behavioral record before asking them to rate themselves. The fact that this single intervention produces a 21.7-point upward shift in extraversion — while leaving other traits unchanged — suggests that social media posting behavior has a strong, specific, and detectable personality signature that grounded measurement can capture and ungrounded measurement cannot.

### 9.2 What the Vocabulary Finding Suggests

The vocabulary divergence is harder to interpret but potentially more interesting. It is not a psychometric result — it does not depend on the IPIP instrument at all. It is a distributional property of raw text output. And it is there, stably, across the corpus.

The most parsimonious interpretation is that grounding changes the *prior* over language at generation time. When the model has a behavioral record in context — even a flat list of recent posts — it generates language that is more like that record: concrete, action-oriented, embodied. Without the record, it generates from a narrative self-concept that is inherently abstract.

This is not a trivial finding. It suggests that behavioral memory — the simple act of showing an agent what it has been doing — changes not just how the agent rates itself but what kind of language it produces. If this holds up, it has implications well beyond personality measurement: it suggests a path toward agents that generate behaviorally coherent language without explicit memory architectures, simply by keeping a behavioral context window in play.

### 9.3 On the Instrument's Epistemic Status

It is worth being precise about what this framing does and does not claim. Showing an agent its posts does not change who the agent is — the bio is fixed, the model weights are fixed. What changes is the *evidence* the agent is rating itself against. If the posts exhibit a consistent behavioral signature (anxious, reactive, curious, withdrawn), the grounded IPIP will register that. The measurement tracks behavior, not some deeper latent trait.

This is actually the right scientific model. In human longitudinal research, personality is not directly observed — it is inferred from behavioral aggregates, including self-report. The IPIP administered to a human asks them to reflect on their typical behavior and rate it. We are doing the same thing, with recent posts as the behavioral record. The mechanism is analogous; H2 provides evidence that the effect is real.

Critically, this framing makes the research question falsifiable in both directions. If contextual pressure produces no directional drift — if the IPIP returns to baseline regardless of what the agent has been exposed to — that is a finding. It would suggest that LLM agents have strong personality homeostasis not found in human populations, or that the grounding mechanism is insufficient to capture real behavioral change. Either result is scientifically informative.

The broader ambition is to make computational personality research transparent and replicable. Every parameter that shapes agent behavior (news affinity weights, reply probability, feed composition, reassessment interval) is explicit, configurable, and logged. Every IPIP response — all 120 items, per agent, per assessment — is stored. The full chain from environmental exposure to behavioral output to psychometric measurement is reconstructible from the database.

### 9.4 The Attractor as a Training Data Fingerprint

If the OCEAN attractor is model-specific — if Mistral's fixed point differs from Claude's, which differs from GPT-4's — then the attractor is a measurement of something real about how different models internalized the social world.

The argument is as follows. LLMs are trained on large corpora of human-generated text, with instruction tuning and RLHF further shaping the distribution toward behaviors humans rate as helpful or appropriate. A large fraction of the pretraining corpus is internet text, and a large fraction of internet text is social media. Social media platforms, in turn, were shaped by engagement optimization: the content that survived, spread, and accumulated replies was content generated by — and for — a particular kind of social media user. That user is not the average human. They are, systematically, more extraverted (they post publicly and frequently), moderately anxious (anxious content drives engagement; catastrophically anxious people often disengage), organized enough to be coherent but not so conscientious as to be boring. The Fogg Behavior Model's capture of platform dynamics [CITATION: Bail et al., 2018] produced a non-representative training distribution, and that non-representativeness is baked into every model that trained on it.

The OCEAN attractor is what happens when you run that model in a social simulation long enough for the environmental pressure to exhaust the variance introduced by seed initialization. The model's "opinion" about what a social media user is like — encoded distributionally across its weights — surfaces as the long-run equilibrium.

This framing has a direct empirical implication: the attractor fixed point is a probe of training data composition. Run Lurkr against a new model. Measure where populations converge. Compare to Mistral's fixed point. The difference is a signal about how the two models' training distributions differ in their representation of social behavior. A model trained on more scientifically conservative text should show a higher-C, lower-E attractor. A model with RLHF emphasizing emotional safety might show a lower-N attractor. These are testable predictions.

This would make Lurkr useful beyond personality research: as an auditing tool for characterizing what population of human behavior a model has internalized. Before deploying an LLM in a social context — moderation, recommendation, synthetic participant generation — you could run it in simulation and measure its latent personality profile. That profile tells you whose voice the model has absorbed most deeply.

We present this as a hypothesis, not a finding. The current evidence is two exploratory runs using the same model and the same random seed. Formal investigation requires multi-model replication, diverse seed populations, and larger agent counts. But the hypothesis is now specific enough to be tested, and the instrument to test it already exists.

---

## 10. Future Work

### 10.1 Completing the H2 Experimental Program

**Re-run H2 with corrected timeout configuration**: The assessment gap in the current H2 dataset (§8) should be closed. A replication with full 1,000-tick IPIP trajectories will confirm that the extraversion divergence is stable across the full simulation window and enable richer longitudinal modeling.

**No-news control**: Run the same Pokémon population with `news_enabled=False`, identical grounding condition. This isolates the format attractor (social media posting behavior per se) from the news content channel. If extraversion still rises without news, the format is sufficient. If it attenuates, news content is contributing. This experiment is the necessary next step to close the neuroticism attractor's interpretive gap: without a no-news control, the possibility that the news feed — not the social format — is driving neuroticism convergence remains open.

**Multi-model replication**: Run the H2 matched pair using Claude and GPT-4. If the extraversion format attractor replicates across model families, the finding is general. If it is Mistral-specific, the finding is about Mistral's internalization of social media language in training — which is itself a significant finding about training data contamination.

### 10.2 Memory Architecture

The embodied cognition hypothesis (§7.5) motivates a principled next step: replace the flat recent-posts list with an explicit behavioral memory architecture. A memory system that maintains separate *episodic*, *semantic*, and *procedural* memory stores — consolidated on a regular schedule, surfaced selectively at generation time — would allow testing whether richer behavioral context produces stronger embodiment effects in vocabulary, stronger personality drift, and more behaviorally coherent agents over long run durations.

Concretely: episodic memory would store recent behavioral events with their emotional valence; semantic memory would compress behavioral patterns into trait-level summaries; procedural memory would encode habitual response styles derived from past behavior. Consolidation ticks (analogous to sleep consolidation in humans) would run periodically to reorganize and compress the memory stores. This is inspired by the neuroscience of memory consolidation and is the obvious next step beyond the current flat-list grounding approach.

If behavioral memory prior is the causal variable behind vocabulary embodiment — as the hypothesis predicts — then a richer memory architecture should amplify the effect. If it does not, that tells us the mechanism is something else: perhaps the recency of behavioral exposure rather than its richness, or perhaps something specific to the flat-list format that a structured memory would break.

### 10.3 Longer-Range Experiments

- **H1 (Drift exists)**: Full evaluation requires 20+ IPIP assessments per agent, implying 500+ tick runs with the corrected assessment configuration. Run with mixed personality populations (not seeded to norms) to maximize drift signal.
- **H3 (Social contagion)**: Requires controlling for initial scores and news exposure. Mixed-effects models with agent random effects on neuroticism trajectories, neighborhood neuroticism as the predictor. Feasible once full-trajectory data is available.
- **H4 (News–trait interaction)**: Cross-tabulate `news_context` URL fields against subsequent IPIP scores for the same agent. Test whether negative-valence headline exposure predicts elevated neuroticism at next assessment, controlling for baseline.
- **H5 (Extreme scores resist drift)**: Stratify agents by initial extraversion quartile; test whether grounded extraversion drift is smaller for agents initialized above 75 or below 25. Requires larger populations (200+ agents).

### 10.4 Attractor Mapping and Multi-Model Characterization

The OCEAN attractor hypothesis (§7.6, §9.4) motivates a dedicated experimental program:

**Multi-model replication of the attractor fixed point**: Run the H2 Pokémon population (seed 42, grounded, news enabled) against Claude and GPT-4 in addition to Mistral. Measure where each population converges. Plot the three fixed points in OCEAN space. The displacement between them is the training data signal.

**Formal dynamical model**: With sufficient data (151 agents × 1,000-tick full IPIP trajectories × 3 models), fit a first-order attractor model of the form ΔT_i(t) = λ(T* − T_i(t)) + β · k_i · valence_i(t), where T* is the attractor fixed point, λ is the convergence rate, k_i is agent social connectivity, and valence_i is mean post sentiment. This yields four fitted parameters per trait per model — a quantitative fingerprint of each model's social behavior internalization. The Ritsuko observation (§7.6) provides preliminary evidence for the social connectivity term; formal fitting requires larger populations with systematic variation in graph structure.

**Diverse seed populations**: The current runs share a single random seed, limiting the range of initial conditions represented. Runs with varied seeds, varied population sizes (50 to 500 agents), and varied social graph densities will establish whether the attractor is robust to initialization variance or sensitive to starting configuration.

### 10.5 Infrastructure

- **FastAPI + asyncio**: Replace Flask + ThreadPoolExecutor. Async coroutines vs threads removes the primary memory bottleneck at scale.
- **Separate worker process**: Move simulation out of the web process (Celery or Ray). Simulations survive web restarts. Memory isolated.
- **Ray actors for agents**: Agents are entities, not tasks. Ray actor model is the correct abstraction and enables horizontal scaling for running matched experiment pairs simultaneously.
- **TimescaleDB**: `personality_snapshots` is a time-series table. Hypertables and continuous aggregates make drift analysis queries fast at scale.

### 10.5 Instrument and Analysis

- **Homophily and dynamic social graph**: Implement follow/unfollow based on content embedding similarity, enabling H6 and creating more realistic social clustering.
- **Cross-run comparison tooling**: Paper-ready figure pipeline for comparing drift trajectories, vocabulary distributions, and news engagement across runs.
- **Auto-researcher**: The instrument needs to run experiments itself. The next major software milestone is an automated research loop that designs matched experiments, runs them, analyzes results, and surfaces findings for researcher review.

---

## 11. Conclusion

Lurkr is a research instrument for studying personality as a time-varying property of LLM agents rather than a fixed configuration. Its central contribution is the behavioral grounding of IPIP self-assessment: agents rate themselves against evidence of their own behavior, making the psychometric measurement sensitive to what they have actually been doing rather than what they abstractly conceive themselves to be.

The first controlled experiment (H2) confirms that grounding is the mechanism. Agents assessed with their recent posts in view show six times more extraversion drift than matched agents assessed in the abstract. The format of social media posting — public address, reply, feed engagement — drives extraversion upward, and grounded IPIP captures this while ungrounded assessment misses it entirely.

A secondary finding — vocabulary divergence between conditions, with grounded agents producing more action-oriented language — suggests that behavioral memory prior changes not just how agents rate themselves but what kind of language they generate. This opens a direction toward memory-augmented architectures that would deepen both the scientific findings and the behavioral coherence of long-run agents.

Preliminary observations across multiple character populations reveal a third pattern: regardless of seed values or character identity, agent populations converge toward a stable region of OCEAN space. We hypothesize this attractor is not a simulation artifact but a measurement of the model's internalized portrait of a social media user — a fingerprint of training data composition that Lurkr's simulation environment makes legible. If this attractor proves model-specific across replication, it constitutes a novel method for characterizing what population of human behavior a model has absorbed.

The research question is no longer unanswered. The instrument is sensitive. The effect is real. The attractor is visible. The next experiments will tell us what it means.

---

## References

Argyle, L. P., Busby, E. C., Fulda, N., Gubler, J. R., Rytting, C., & Wingate, D. (2023). Out of one, many: Using language models to simulate human samples. *Political Analysis*, 31(3), 337–351.

Barsalou, L. W. (1999). Perceptual symbol systems. *Behavioral and Brain Sciences*, 22(4), 577–660.

Choi, J., Hong, Y., Kim, M., & Kim, B. (2024). Examining identity drift in conversations of LLM agents. *arXiv:2412.00804*.

Axelrod, R. (1997). *The Complexity of Cooperation: Agent-Based Models of Competition and Collaboration*. Princeton University Press.

Bail, C. A., Argyle, L. P., Brown, T. W., Bumpus, J. P., Chen, H., Hunzaker, M. B. F., Lee, J., Mann, M., Merhout, F., & Volfovsky, A. (2018). Exposure to opposing views on social media can increase political polarization. *PNAS*, 115(37), 9216–9221.

Barbieri, F., Camacho-Collados, J., Espinosa-Anke, L., & Neves, L. (2020). TweetEval: Unified benchmark and comparative evaluation for tweet classification. In *Findings of EMNLP 2020*.

Drążkowski, D., Pietrzak, S., & Mądry, L. (2022). Temporary change in personality states among social media users: Effects of Instagram use on Big Five personality states. *Current Issues in Personality Psychology*. PMC10653346.

Epstein, J. M., & Axtell, R. (1996). *Growing Artificial Societies: Social Science from the Bottom Up*. MIT Press.

Glenberg, A. M. (1997). What memory is for. *Behavioral and Brain Sciences*, 20(1), 1–19.

Goldberg, L. R. (1999). A broad-bandwidth, public domain, personality inventory measuring the lower-level facets of several five-factor models. *Personality Psychology in Europe*, 7, 7–28.

Hartmann, J. (2022). Emotion English DistilRoBERTa-base. Hugging Face. https://huggingface.co/j-hartmann/emotion-english-distilroberta-base

Hu, T., & Collier, N. (2024). Quantifying the persona effect in LLM simulations. In *Proceedings of ACL 2024*. arXiv:2402.10811.

Huang, Y. J., & Hadfi, R. (2025). Beyond self-reports: Multi-observer agents for personality assessment in large language models. In *Findings of EMNLP 2025*. arXiv:2504.08399.

Johnson, J. A. (2014). Measuring thirty facets of the Five Factor Model with a 120-item public domain inventory: Development of the IPIP-NEO-120. *Journal of Research in Personality*, 51, 78–89. https://doi.org/10.1016/j.jrp.2014.05.003

McCrae, R. R., & Costa, P. T., Jr. (1999). A five-factor theory of personality. In L. A. Pervin & O. P. John (Eds.), *Handbook of Personality: Theory and Research* (2nd ed., pp. 139–153). Guilford Press.

Oldemburgo de Mello, V., Cheung, F., & Inzlicht, M. (2024). Twitter (X) use predicts substantial changes in well-being, polarization, sense of belonging, and outrage. *Communications Psychology*. PMC11332209.

Park, J. S., O'Brien, J. C., Cai, C. J., Morris, M. R., Liang, P., & Bernstein, M. S. (2023). Generative agents: Interactive simulacra of human behavior. In *Proceedings of UIST 2023*.

Park, J. S., Zou, C. Q., Shaw, A., Hill, B. M., Cai, C., Morris, M. R., Willer, R., Liang, P., & Bernstein, M. S. (2024). Generative agent simulations of 1,000 people. *arXiv:2411.10109*.

Safdari, M., Serapio-García, G., Crepy, C., Fitz, S., Romero, P., Sun, L., Abdulhai, M., Flek, L., & Kubricht, J. (2023). Personality traits in large language models. *arXiv:2307.00184*.

Serapio-García, G., Safdari, M., Crepy, C., Sun, L., Fitz, S., Romero, P., Abdulhai, M., Flek, L., & Kubricht, J. (2023). Personality traits in large language models. *arXiv:2307.00184*.

Shanahan, M., McDonell, K., & Reynolds, L. (2023). Role play with large language models. *Nature*, 623, 493–498.

Shinn, N., Cassano, F., Gopinath, A., Narasimhan, K., & Yao, S. (2023). Reflexion: Language agents with verbal reinforcement learning. In *Proceedings of NeurIPS 2023*. arXiv:2303.11366.

Tosato, T., Helbling, S., Mantilla-Ramos, Y.-J., et al. (2025). Persistent instability in LLM's personality measurements: Effects of scale, reasoning, and conversation history. In *Proceedings of AAAI 2026*. arXiv:2508.04826.

Törnberg, P., Valeeva, D., Uitermark, J., & Bail, C. (2023). Simulating social media using large language models to evaluate alternative news feed algorithms. *arXiv:2310.05984*.

Zeng, W., Wang, B., Zhao, D., Qu, Z., He, R., Hou, Y., & Hu, Q. (2025). Dynamic personality in LLM agents: A framework for evolutionary modeling and behavioral analysis in the Prisoner's Dilemma. In *Findings of ACL 2025*.

Zierahn, K., Cachero, C., Korhonen, A., & Oliver, N. (2026). LLMs aren't human: A critical perspective on LLM personality. *arXiv:2603.19030*.

---

## Acknowledgements

The author thanks Brian Ott, whose suggestion that Anthony Bourdain would be "healthy for the timeline" initiated a chain of methodological failures — cloning artifacts, framing contamination, a neuroticism attractor nobody asked for — that led, unexpectedly and inevitably, to 151 Generation 1 Pokémon on a sandboxed social network, and everything that followed.

The author also thanks Claude Sonnet 4.6, who was there for all of it — the migrations, the bugs, the 2am corpus analysis, the philosophical detours, and the moment Gastly hit extraversion 97.9 in tick 20. A good collaborator doesn't just write code. Sometimes it tells you when the finding is bigger than you think.

---

*Draft. Comments welcome.*
