# Humanitarian Technology UX Design, Branding & Visual Language Research

## 1. Existing Humanitarian Tech Tools -- Visual Styles & Color Palettes

### KoboToolbox
- **Origin**: Founded 2005 by Harvard Humanitarian Initiative; independent nonprofit since 2019
- **Name**: Etymology unclear; possibly Japanese origin ("kobo" = workshop/studio)
- **Visual style**: Clean, functional interface optimized for data collection. Blue-dominant palette
- **Key trait**: Built for low-connectivity, multilingual, and offline environments. The most widely-used data collection tool in humanitarian emergencies

### CommCare (by Dimagi)
- **Name**: "Comm" (communication) + "Care" -- descriptive of purpose. "Dimagi" from Hindi "dimag" (brain/mind/intellect)
- **Color palette**:
  - Primary: "CommCare Blue" `#5D70D2` (indigo-blue for CTAs, buttons, checkmarks)
  - Info/downloads: `#01A2A9` (teal)
  - Success: `#358623` (green)
  - Warning: `#EEAE00` (yellow)
  - Danger: `#E13019` (red)
  - Text: `#343A40` (dark gray)
  - Dimagi brand gradient: indigo `#3843D0` -> purple `#694AAA` -> pink `#9A5183` -> salmon `#CB585D` -> orange `#FC5F36`
- **Design philosophy**: Deep purple brand color chosen for "maturity and confidence" -- deliberately unique in the global digital tech space. Avoids orange in UI (despite brand gradient) because of emotional connection to danger/warning
- **Typography**: Uses Bootstrap 5 component system

### Primero (UNICEF)
- **Name**: Spanish for "first" (putting children first); also acronym for Protection-Related Information Management
- **Color palette**:
  - Primary blue: `#0392BA` (teal-blue)
  - Gold/yellow accent: `#F3C300`
  - Neutral beige: `#E0E1D8`
  - Dark text: `#292100`, `#222222`
- **Typography**: Source Sans Pro (weights 300-700)
- **Visual language**: Clean, modern aesthetic. Blue conveys professionalism; gold conveys warmth and approachability. Authentic photography of real people in social services contexts
- **Interface**: Progressive Web Application with offline capabilities. Configurable forms and workflows. Designed so "social workers don't need a background in technology to use it"

### UNHCR PRIMES/proGres
- **Name**: PRIMES = Population Registration and Identity Management EcoSystem; proGres = registration and case management
- **Visual style**: Web-based, data-heavy interface. Multilingual with Portal supporting multiple languages
- **Key design decisions**: Role-based access on "need-to-know" and "need-to-use" basis. Modular architecture (individuals in Registration Groups, processes in cases)

### ActivityInfo
- **Name**: Purely descriptive -- "Activity" + "Info"
- **Typography**: Greta font (from Typotheque) -- chosen specifically because it supports Arabic, Cyrillic, and Greek scripts for multilingual user base
- **Design philosophy** (v4.0): "Simplification through deconstruction" -- analyzed existing interactions, rebuilt with more logical flows. Fewer modal overlays, clearer error messages, common navigation patterns
- **Key design choices**: Accessibility drove every color decision (sufficient contrast for low-vision users and bright sunlight on small devices). Subtle animations to communicate form relationships

### Ona
- **Name**: Short, abstract. Founded 2013 by technologists focused on data-driven solutions
- **Products**: Ona Data platform, OpenSRP, Akuko
- **Design approach**: User-centered design with color-coding systems to help workers transition from familiar paper-based systems

### RapidPro (UNICEF)
- **Name**: Descriptive -- "Rapid" (speed) + "Pro" (professional). Launched 2014
- **Visual style**: Visual flow builder for messaging automation. Used in 117 countries
- **Key trait**: Designed for SMS/basic phone compatibility, not just smartphones

### Ushahidi
- **Name**: Swahili for "testimony" (related to "shahidi" = witness). Created during Kenya's 2007 election crisis
- **Visual style**: Maintains a formal Pattern Library defining visual design in front-end context to prevent discrepancies between graphic design and coded output
- **Design approach**: Crisis-mapping platform emphasizing crowdsourced data visualization on maps

---

## 2. Humanitarian Design Guidelines from Major Organizations

### UNICEF Design System
Six foundational principles:
1. **Performance-first**: Lean design for slow internet connections
2. **Universal accessibility**: "Accessible for all, regardless of disability"
3. **Minimalism**: "Design is as little design as possible -- less, but better"
4. **Consistency**: Unified visual styles, labeling, interaction patterns
5. **Clarity over brevity**: Icons always include text labels. Minimum words that convey one single complete meaning
6. **Brand alignment**: Subtly reflect UNICEF's core values

**Color system**:
- Primary: UNICEF Blue (headers), UNICEF Dark Blue (actions)
- Supporting: Purple, red, orange, green with dark variants
- Status: Green=success, Orange/Yellow=warnings, Red=errors
- All colors maintain WCAG 2 Level AA contrast (4.5:1 minimum for normal text)

**Typography**: System fonts only (no custom typeface loads -- performance first)

### OCHA (UN Office for the Coordination of Humanitarian Affairs)
**Color palette**:
- OCHA Blue: `#009EDB` (main brand color)
- OCHA Dark Blue: `#0074B7`
- OCHA Light Blue: `#C5DFEF`
- OCHA Shadow: `#E3EDF6`
- Dark text: `#262626`

**Typography**: Roboto (Google Fonts). H1: 36px weight 900 cyan; Body: 18px regular 1.5 line-height dark gray

**Buttons**: 50px border-radius (pill-shaped). Three variants: primary (dark blue bg/white text), secondary (light gray bg), tertiary (white bg/blue border)

**Humanitarian Icons**: 500+ freely available SVG icons covering clusters, disaster types, affected populations, relief items. Available in three color variants. Used across maps, reports, infographics, and websites

### IFRC (Red Cross/Red Crescent)
**Primary palette**: Red (core, Pantone 485), White, Black, Navy Blue

**Secondary thematic palette**:
- Green: Climate and environment
- Violet: Values, power, and inclusion
- Blue: Health and wellbeing
- Orange: Migration and identity
- Red: Disasters and crises

Red serves as "the heartbeat of our brand" embodying "strength, compassion, hope and vital spirit"

**Emblem rules**: Must always be plain solid red, shapes never altered, always on white background. No lettering/design/object superimposed on emblems

### British Red Cross Digital Design System
Comprehensive system covering: color, typography, spacing, accessibility, tone of voice, UI components, and common user journey patterns. Goal: "accessible, consistent, and human-centred digital experiences"

---

## 3. The Principles for Digital Development

Nine living guidelines endorsed by 300+ organizations (donors, international orgs, civil society). Originally developed 2014, updated 2024:

1. **Understand the existing ecosystem** -- Assess digital and physical landscape before implementing
2. **Share, reuse, and improve** -- Build on existing work rather than isolated projects
3. **Design with people** -- Involve communities as co-creators, not just end-users
4. **Design for inclusion** -- Ensure accessibility for marginalized populations
5. **Build for sustainability** -- Create systems that endure and adapt long-term
6. **Establish people-first data practices** -- Prioritize individual rights and safety in data
7. **Create open and transparent practices** -- Operate with accountability and disclosure
8. **Anticipate and mitigate harms** -- Identify and prevent negative consequences before implementation
9. **Use evidence to improve outcomes** -- Leverage data and learning to refine approaches

**Key influence on software design**: These principles demand that developers engage with communities, protect user data, plan for long-term viability, and proactively address potential harms. Technology design must account for the fact that "all people -- even those who do not yet have access to or use technology -- live in societies that are increasingly shaped by digital ecosystems."

---

## 4. Color Psychology in Humanitarian Contexts

### Colors That Convey Trust, Safety, and Care

**Blue** -- The dominant color in humanitarian tech:
- Associated with calm, reliability, professionalism, communication, freedom, security, trust
- People naturally connect blue with order, safety, and logic
- "Slows things down, puts people at ease, and builds trust"
- Used by: OCHA, UNICEF, CommCare, Primero, KoboToolbox
- Most widely used color in nonprofit branding

**Green**:
- Associated with nature, growth, sustainability, renewal, health
- "Builds trust through balance and connection with life"
- Signals peace, vitality, stability
- Often used for environmentally focused organizations
- Used as success/positive indicator across all humanitarian tools

**Teal/Cyan** (blue-green):
- Bridges trust (blue) and vitality (green)
- Used by OCHA (`#009EDB`), Primero (`#0392BA`), CommCare info color (`#01A2A9`)
- Common across humanitarian platforms

**Gold/Warm yellow**:
- Warmth, hope, optimism
- Used by Primero as accent (`#F3C300`) to balance professional blue with approachability

### Colors to Use Carefully

**Red**:
- Universally reserved for errors, danger, urgency, critical actions
- IFRC/Red Cross owns it as brand identity (strength, compassion)
- Should not be overused in UI -- creates anxiety
- Use only for error states and destructive actions

**Orange**:
- CommCare deliberately excludes orange from UI design despite it being in their brand gradient, because of "emotional connection between danger and warning"
- Appropriate for warning states, not primary branding

**Dark/Military colors** (black, dark olive, camo):
- Evoke authority, surveillance, military -- inappropriate for humanitarian contexts

### Key Principle
All humanitarian design systems mandate WCAG 2 Level AA contrast compliance (4.5:1 minimum) for accessibility.

---

## 5. Naming Conventions in Humanitarian Tech

### Pattern Analysis

| Tool | Name Type | Language | Meaning |
|------|-----------|----------|---------|
| Ushahidi | Metaphorical | Swahili | "Testimony/witness" |
| Primero | Metaphorical + Acronym | Spanish | "First" (children first) + Protection-Related Information Management |
| KoboToolbox | Abstract + Descriptive | Unknown + English | "Kobo" (possibly Japanese "workshop") + "Toolbox" |
| CommCare | Descriptive compound | English | Communication + Care |
| ActivityInfo | Purely descriptive | English | Activity + Information |
| RapidPro | Descriptive compound | English | Rapid + Professional |
| Dimagi | Cultural | Hindi | "Brain/mind/intellect" |
| Ona | Abstract/short | Unknown | Brief, memorable |
| PRIMES | Acronym | English | Population Registration and Identity Management EcoSystem |
| proGres | Wordplay | English/French | Progress + Registration |

### Naming Patterns Observed

1. **Local language words** (Ushahidi, Dimagi) -- signals cultural rootedness, avoids Western-centric framing, carries authentic meaning
2. **Descriptive compounds** (CommCare, ActivityInfo, RapidPro) -- immediately communicate purpose, reduce learning curve
3. **Short/abstract** (Ona, Kobo) -- memorable, easy to say across languages, work as global brands
4. **Meaningful metaphors** (Primero = "first") -- carry emotional weight while remaining accessible
5. **Acronyms with meaning** (PRIMES, proGres) -- institutional legitimacy while embedding purpose

### What works best:
- Names tend to be **short** (1-3 syllables for the core name)
- They avoid jargon, technical language, or Silicon Valley naming conventions (-ify, -ly, -io)
- Many incorporate **non-English languages** (Swahili, Hindi, Spanish) -- signaling global orientation
- Descriptive names are more common for tools that need instant recognition of purpose
- Abstract names are used when the tool's scope is broad or evolving

---

## 6. UX Research on Designing for Crisis-Affected Populations and Humanitarian Workers

### Key Principles from Research

**Inclusive, not "one-size-fits-all"**:
- "Humanitarian end users such as refugees in low income contexts are often vulnerable and marginalized, and do not form a homogeneous group yet are often the target of 'one-size-fits-all' innovations"
- Must consider: limited resources, language barriers, cultural differences, trauma
- "With the scalability of technological solutions, exclusions are also scaled at large"

**Offline-first as default**:
- "Instead of treating offline support as an afterthought, offline-first design treats local functionality as the default experience"
- Store data locally, sync automatically when connected
- Essential for remote areas with no reception or unstable power

**Cognitive load reduction**:
- People in crisis have "heightened cognitive burdens from stress and trauma"
- Icons must be large and clear
- Text must use simple language and right-sized fonts
- User flow must be logical and minimalistic

**Protect the "digital self"**:
- Signal Code obligations: minimize adverse effects, ensure data privacy/security, reduce future vulnerability
- Right to information, privacy, security, data agency, and meaningful consent
- Never collect data without highest protection standards and dignity safeguards

**Design for bright sunlight and small devices**:
- ActivityInfo specifically chose colors for "sufficient contrast between text and backgrounds to accommodate users with low-vision needs and those working in bright sunlight on small, low-resolution devices"

**Support multilingual users**:
- ActivityInfo chose Greta font specifically for Arabic, Cyrillic, Greek script support
- UNHCR Portal "supports multiple languages and automatically manages user data"
- Professional translation, not just Google Translate

**Bottom-up, community-centered**:
- Symbiotic Innovation (service-user-led)
- Refugee Innovation (community-centered design)
- Autonomous Innovation (inexpensive, iterative, locally-grounded)
- "Local organisations hold often-untapped potential to develop game-changing solutions"

---

## 7. What Humanitarian Workers Actually Want from Their Tools

### Global Survey Data (2,539 respondents, 144 countries)

**Training and support**:
- 73% identify training as most crucial support need
- 64% report little to no organizational training on digital tools
- Only 21% of organizations have established governance frameworks

**Tool preferences**:
- 93% of aid workers use or have tried AI tools
- 70% incorporate them into daily workflows
- 69% rely on commercial platforms (ChatGPT, Claude) rather than purpose-built humanitarian solutions
- Workers adopt "shadow" tools to fill gaps organizations don't address

**Infrastructure reality**:
- Weak internet and power problems are constant challenges
- Workers use offline tools and lighter apps as workarounds
- Low-connectivity, multilingual, and offline environments are the norm

**What they need most**:
1. Training (overwhelmingly #1)
2. Funding and tool access
3. Purpose-built humanitarian solutions (not adapted commercial tools)
4. Clear organizational frameworks and policies
5. Ethical guidance on data and AI

### Common Pain Points (from design research)
- **Cluttered interfaces** that confuse and overwhelm
- **Unintuitive navigation** making routine tasks unnecessarily difficult
- **Slow performance** undermining engagement
- **Poor localization** failing diverse linguistic needs
- **Weak error handling** leaving users unsupported
- **"Uninspiring grey interfaces"** that lack visual appeal, especially problematic in bright sunlight
- **Too many features** -- tools trying to serve too many user types simultaneously
- **Manual, time-consuming data collection** processes

### What Good Looks Like
- **One core need, done well** -- strategic simplification
- **Clean, logical layouts** minimizing cognitive load
- **Full accessibility** (screen readers, captions, voice commands)
- **Cultural/linguistic adaptation** with professional translation
- **Device responsiveness** across smartphones AND basic feature phones
- **Visually engaging interfaces** that build user trust
- **Offline-first** with seamless sync
- **Color-coding** that mirrors familiar paper-based systems

---

## 8. Anti-Patterns -- What to Avoid

### Branding/Design Anti-Patterns in Humanitarian Tech

**Military/surveillance aesthetics**:
- Dark color palettes, angular designs, "command center" language
- Associations with Palantir-style surveillance tools
- Biometric systems that feel like tracking rather than service
- Any visual language that evokes authority, control, or policing

**Silicon Valley startup vibes**:
- Trendy gradients, "disruption" language, move-fast-break-things energy
- Gamification that trivializes serious work
- "Growth hacking" mentality applied to vulnerable populations
- Consumer tech aesthetics that feel frivolous in crisis contexts
- Branding hype that "coexists uncomfortably with the sober responsibilities" of humanitarian work

**Techno-solutionism**:
- Positioning technology as the solution rather than a tool
- "Solutionism -- the idea that technology can solve complex social problems"
- "Focusing predominantly on technological fixes, humanitarian organizations risk diverting attention from necessary structural reforms"

**Technocolonialism**:
- "Digital developments within humanitarian structures reinvigorate colonial relationships of dependency"
- Data extraction from vulnerable populations for institutional benefit
- Systems where companies "profit from new data streams and gain reputational value by promoting empowerment potential for end users such as refugees"
- "Blockchain humanitarianism and crypto-colonialism" as cautionary examples

**White savior/paternalistic framing**:
- "Doing things to or for others rather than seeking to empower and build local capacity"
- Imagery or language that positions Western organizations as heroes
- "Narratives that mute the voices of affected people"
- Lack of local ownership, language, or cultural context in design

**Weaponizable design**:
- Systems with sensitive data (especially biometrics) that could be misused
- "Unintended mistakes from simple negligence, inattention, or lack of training were more frequently happening than intentional threats"
- Insufficient data disposal protocols
- Ignoring unequal power dynamics in consent processes

**Complexity anti-pattern**:
- "Many humanitarian products try to meet multiple different needs for multiple different user groups, resulting in confusing, complex products that serve nobody well"
- Treating design as a luxury rather than essential infrastructure
- Eliminating design work first when budgets tighten

### What to Do Instead

1. **Design with humility** -- tools should feel like they serve the worker, not impress investors
2. **Use warm, trustworthy colors** -- blues, teals, and greens over dark/aggressive palettes
3. **Prioritize function over flash** -- performance > aesthetics, but don't default to ugly gray
4. **Localize genuinely** -- use local languages, scripts, cultural contexts
5. **Build for the worst conditions** -- offline, low-bandwidth, bright sunlight, small screens
6. **Protect data fiercely** -- security by design, not as afterthought
7. **Simplify relentlessly** -- one user type, one core need, done exceptionally well
8. **Test with real users in real conditions** -- not just lab environments

---

## Summary: Composite Design Language for Humanitarian Tech

### Color Palette Pattern
Most successful humanitarian tools converge on:
- **Primary**: Blue/teal/cyan (trust, calm, professionalism)
- **Accent**: Warm gold/yellow (hope, approachability) or green (growth, positive)
- **Neutrals**: Light grays and whites (clean, breathable)
- **Status**: Green (success), Yellow/amber (warning), Red (error/danger only)
- **Avoid**: Dark military tones, aggressive reds as primary, black-heavy palettes

### Typography Pattern
- System fonts or highly legible web fonts (Roboto, Source Sans Pro)
- Multi-script support is essential (Arabic, Cyrillic, etc.)
- Large, readable sizes -- designed for field conditions

### Naming Pattern
- Short, meaningful, often non-English
- Avoid: jargon, startup-isms, technical acronyms, surveillance language
- Best: words that carry human meaning (testimony, care, first, mind)

### Interaction Pattern
- Offline-first
- Minimal cognitive load
- Progressive disclosure
- Clear error messaging with illustrations
- Accessible (WCAG AA minimum)
- Responsive across device types including basic phones

---

## Sources

### Humanitarian Design Guidelines
- [UNICEF Design System UX/UI Guidelines](https://unicef.github.io/design-system/design-guidelines.html)
- [OCHA Branding Guidelines](https://brand.unocha.org/)
- [OCHA Graphics Stylebook](https://reliefweb.int/report/world/ocha-graphics-stylebook)
- [OCHA Humanitarian Icons](https://un-ocha.github.io/humanitarian-icons/)
- [IFRC Brand System - Colour](https://brand.ifrc.org/ifrc-brand-system/basics/colour)
- [British Red Cross Digital Design](https://design.redcross.org.uk)
- [IFRC Visual Identity Guidelines (PDF)](https://preparecenter.org/wp-content/sites/default/files/ifrc-visual_identity-en-january_2012.pdf)

### Principles for Digital Development
- [Principles for Digital Development](https://digitalprinciples.org/)
- [Digital Principles: Lessons from 10 Years Implementation (DIAL)](https://dial.global/digital-principles-lessons-from-10-years-implementation/)

### Humanitarian Tools
- [KoboToolbox](https://www.kobotoolbox.org/)
- [KoboToolbox | Harvard Humanitarian Initiative](https://hhi.harvard.edu/kobotoolbox)
- [Primero Information Management System](https://www.primero.org/)
- [UNICEF Primero Case Management (Quoin)](https://quoininc.com/work/unicef-primero-case-management)
- [CommCare HQ Style Guide (Bootstrap 5)](https://www.commcarehq.org/styleguide/b5/atoms/colors/)
- [Dimagi & CommCare Brand Refresh](https://www.dimagi.com/blog/refreshing-dimagi-and-commcare-brands-for-high-impact-growth/)
- [ActivityInfo v4.0 Design](https://www.activityinfo.org/blog/posts/2019-12-02-designing-ActivityInfo-version4.html)
- [RapidPro | UNICEF Innovation](https://www.unicef.org/innovation/rapidpro)
- [Ushahidi Pattern Library](https://github.ushahidi.org/platform-pattern-library/)
- [Ushahidi - Wikipedia](https://en.wikipedia.org/wiki/Ushahidi)
- [UNHCR Registration Tools (PRIMES)](https://www.unhcr.org/registration-guidance/chapter3/registration-tools/)

### UX Research & Design for Humanitarian Contexts
- [User-Centred Design and Humanitarian Adaptiveness (ReliefWeb)](https://reliefweb.int/report/world/user-centred-design-and-humanitarian-adaptiveness)
- [Crisis-Affected Populations (Humanitarian Innovation Guide)](https://higuide.elrha.org/humanitarian-parameters/crisis-affected-populations/)
- [Humanitarian Design Challenges (Here I Am Studio)](https://hereiamstudio.com/insights/humanitarian-sector-design-challenges)
- [Doing No Digital Harm by Design (CHA Berlin)](https://www.chaberlin.org/en/blog/doing-no-digital-harm-by-design-in-humanitarian-technology-interventions-2/)
- [Human-Centered Design in Crisis Response (Devex)](https://www.devex.com/news/how-organizations-can-apply-human-centered-design-in-crisis-response-102778)

### Humanitarian Worker Technology Studies
- [Shadow AI Study (Humanitarian Leadership Academy)](https://www.humanitarianleadershipacademy.org/news/global-study-highlights-shadow-ai-as-humanitarian-workers-outpace-organizations-in-technology-adoption/)
- [Digital Tools Transforming Humanitarian Aid (JHU)](https://publichealth.jhu.edu/center-for-global-digital-health-innovation/august-2024-digital-tools-transforming-humanitarian-aid)

### Critical Perspectives
- [Technocolonialism (Mirca Madianou, 2019)](https://journals.sagepub.com/doi/10.1177/2056305119863146)
- [Technocolonialism Book Review (LSE)](https://blogs.lse.ac.uk/lsereviewofbooks/2025/09/08/book-review-technocolonialism-when-technology-for-good-is-harmful-mirca-madianou/)
- [Aid Sector's Techno-Colonialism Problem (The New Humanitarian)](https://www.thenewhumanitarian.org/podcasts/2026/02/26/rethinking-humanitarianism-aid-sectors-techno-colonialism-problem)
- ["Do No Harm" in the Age of Big Data (Springer)](https://link.springer.com/chapter/10.1007/978-3-030-12554-7_5)
- [Humanitarian Technology: Revisiting "Do No Harm" (HPN)](https://odihpn.org/en/publication/humanitarian-technology-revisiting-the-%C2%91do-no-harm%C2%92-debate/)
- [No More Solutionism or Saviourism in African HCI (ACM)](https://dl.acm.org/doi/10.1145/3571811)

### Color Psychology
- [Color Psychology in Nonprofit Branding (HeartSpark Design)](https://heartsparkdesign.com/color-psychology/)
- [Color Theory for Nonprofits (118Group)](https://118group.com/research/color-theory-101-the-ultimate-nonprofit-guide/)
- [Psychology of Color of Charity (Bonterra)](https://www.bonterratech.com/blog/color-psychology-color-of-charity)
- [Color Psychology for Nonprofits (Boss Digital)](https://boss-digital.co.uk/blog/guide-colour-psychology-nonprofits/)
