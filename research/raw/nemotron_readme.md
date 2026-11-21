---
license: cc-by-4.0
task_categories:
- text-generation
language:
- es
tags:
- synthetic
- personas
- NVIDIA
- datadesigner
- sovereign-ai
- el-salvador
size_categories:
- 100K<n<1M
dataset_info:
  features:
  - name: uuid
    dtype: string
  - name: professional_persona
    dtype: string
  - name: sports_persona
    dtype: string
  - name: arts_persona
    dtype: string
  - name: travel_persona
    dtype: string
  - name: culinary_persona
    dtype: string
  - name: family_persona
    dtype: string
  - name: persona
    dtype: string
  - name: cultural_background
    dtype: string
  - name: skills_and_expertise
    dtype: string
  - name: skills_and_expertise_list
    dtype: string
  - name: hobbies_and_interests
    dtype: string
  - name: hobbies_and_interests_list
    dtype: string
  - name: career_goals_and_ambitions
    dtype: string
  - name: sex
    dtype: string
  - name: age
    dtype: int64
  - name: languages_spoken
    dtype: string
  - name: marital_status
    dtype: string
  - name: household_type
    dtype: string
  - name: education_level
    dtype: string
  - name: occupation
    dtype: string
  - name: area
    dtype: string
  - name: municipality
    dtype: string
  - name: department
    dtype: string
  - name: country
    dtype: string
  splits:
  - name: train
    num_bytes: 1193059551
    num_examples: 148000
  download_size: 568403131
  dataset_size: 1193059551
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train-*
---

Nemotron-Personas-El-Salvador
=========================================================================
<center>
  <img src="images/nemotron_personas_el_salvador_approach.png" alt="Nemotron-Personas-El-Salvador" width="400px">
  <p>
    <em>Un enfoque de IA compuesta para personas en español salvadoreño ancladas en distribuciones del mundo real</em><br>
    <em>A compound AI approach to Salvadoran Spanish personas grounded in real-world distributions</em>
  </p>
</center>

# Resumen del conjunto de datos (Dataset Overview)

Nemotron-Personas-El-Salvador es un conjunto de datos de código abierto (CC BY 4.0) compuesto por personas generadas sintéticamente. Este conjunto de datos está anclado en las distribuciones demográficas, geográficas y de rasgos de personalidad reales de El Salvador para capturar la diversidad y la riqueza de la población salvadoreña. Es miembro de la [colección Nemotron Personas](https://huggingface.co/collections/nvidia/nemotron-personas) y el primer conjunto de datos salvadoreño de este tipo alineado con estadísticas de nombres, sexo, edad, estado civil, educación, ocupación y ubicación, entre otros atributos. Esta versión del conjunto de datos se desarrolló en colaboración con [WideLabs](https://www.widelabs.com.br/), miembro de NVIDIA Inception con amplia experiencia apoyando despliegues de IA para el gobierno y sectores regulados en América Latina. El conjunto de datos ofrece personas de alta calidad para una variedad de casos de uso de modelado en español salvadoreño.

Nemotron-Personas-El-Salvador acompaña a los desarrolladores de modelos salvadoreños en la creación de sistemas de [IA Soberana](https://www.nvidia.com/en-us/lp/industries/global-public-sector/sovereign-ai-technical-overview/) que integran datos demográficos y contexto cultural propios de la región. El conjunto de datos mejora la diversidad de los datos generados sintéticamente, mitiga sesgos y previene el [colapso de modelo](https://medium.com/data-science/addressing-concerns-of-model-collapse-from-synthetic-data-in-ai-7cd380208d14) (degradación causada por el entrenamiento no curado sobre las salidas de otro modelo) al reflejar las distribuciones geográficas y demográficas reales de El Salvador. En particular, el conjunto de datos está diseñado para ser más representativo de las distribuciones demográficas subyacentes en múltiples ejes —incluida la diversidad regional en los 14 departamentos, el equilibrio urbano/rural, los niveles de educación, el estado civil y de unión libre, y la estructura del mercado laboral salvadoreño— en comparación con los conjuntos de datos de personas anteriores. Como ejemplo, se pueden producir datos de conversaciones de chat de múltiples turnos de alta calidad con nombres, edades, ocupaciones y trasfondos culturales y educativos reales, todo lo cual aporta perspectivas y ángulos únicos a esos datos.

Producido con [NeMo Data Designer](https://github.com/NVIDIA-NeMo/DataDesigner), un sistema de IA compuesta de nivel empresarial para la generación de datos sintéticos, el conjunto de datos aprovecha un Modelo Gráfico Probabilístico (PGM) propietario junto con el modelo `openai/gpt-oss-120b` (licencia Apache 2.0) y un conjunto en constante expansión de validadores y evaluadores integrados en Data Designer.

Este conjunto de datos está destinado a uso comercial y no comercial.

–

Nemotron-Personas-El-Salvador is an open-source (CC BY 4.0) dataset of synthetically-generated personas. This dataset is grounded in real-world demographic, geographic and personality trait distributions in El Salvador to capture the diversity and richness of the Salvadoran population. It is a member of the [Nemotron Personas collection](https://huggingface.co/collections/nvidia/nemotron-personas), and the first Salvadoran dataset of its kind aligned with statistics for names, sex, age, marital status, education, occupation and location, among other attributes. This version of the dataset was built in collaboration with [WideLabs](https://www.widelabs.com.br/), an NVIDIA Inception member with deep experience supporting government and regulated-sector AI deployments across Latin America. The dataset provides high-quality personas for a variety of modeling use-cases in Salvadoran Spanish.

Nemotron-Personas-El-Salvador supports Salvadoran model builders in developing [Sovereign AI](https://www.nvidia.com/en-us/lp/industries/global-public-sector/sovereign-ai-technical-overview/) systems that incorporate important region-specific demographics and cultural context. The dataset improves diversity of synthetically-generated data, mitigates biases, and prevents [model collapse](https://medium.com/data-science/addressing-concerns-of-model-collapse-from-synthetic-data-in-ai-7cd380208d14) (degradation caused by uncurated training on another model's outputs) by reflecting El Salvador's real geographic and demographic distributions. In particular, the dataset is designed to be more representative of underlying demographic distributions along multiple axes—including regional diversity across all 14 departments, urban/rural balance, education levels, marital and consensual-union status, and the structure of the Salvadoran labor market—as compared to past persona datasets. As an example, one can produce high-quality, multi-turn chat conversation data with real names, ages, occupation, cultural and education backgrounds, all of which bring unique perspectives and angles to that data.

Produced using [NeMo Data Designer](https://github.com/NVIDIA-NeMo/DataDesigner), an enterprise-grade compound AI system for synthetic data generation, the dataset leverages a proprietary Probabilistic Graphical Model (PGM) along with an Apache-2.0-licensed `openai/gpt-oss-120b` model and an ever-expanding set of validators and evaluators built into Data Designer.

This dataset is intended for commercial and non-commercial use.

## Lo que NO está en el conjunto de datos (What is NOT in the dataset)

Dado el énfasis en las personas, el conjunto de datos excluye otros campos disponibles en NeMo Data Designer, p. ej., nombres/apellidos, rasgos de personalidad, etc. También se excluyen las personas generalmente relevantes para clientes empresariales (p. ej., finanzas, salud). [Contáctenos](https://www.nvidia.com/en-us/data-center/products/ai-enterprise/contact-sales/) para explorar casos de uso empresariales.

Todos los datos, aunque reflejan distribuciones del mundo real, son completamente generados de forma artificial. Cualquier similitud en nombres o descripciones de personas con personas reales, vivas o fallecidas, es pura coincidencia.

–

Given the emphasis on personas, the dataset excludes other fields available in NeMo Data Designer, e.g., first/last names, personality traits, etc. Also excluded are personas generally of relevance to enterprise clients (e.g., finance, healthcare). Please [reach out](https://www.nvidia.com/en-us/data-center/products/ai-enterprise/contact-sales/) to explore enterprise use-cases.

All data, while mirroring real-world distributions, is completely artificially generated. Any similarity in names or persona descriptions to actual persons, living or dead, is purely coincidental.

# Desarrollador de los datos (Data Developer)

[WideLabs](https://www.widelabs.com.br/) & NVIDIA Corporation

# Fecha de publicación (Release Date)

Hugging Face 06/03/2026 vía https://huggingface.co/datasets/nvidia/Nemotron-Personas-El-Salvador

# Fecha de creación del conjunto de datos (Dataset Creation Date)

06/03/2026

# Licencia y condiciones de uso (License/Terms of Use)

Este conjunto de datos está licenciado bajo la [Licencia Internacional Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/deed.en) (CC BY 4.0).

–

This dataset is licensed under the [Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/deed.en) (CC BY 4.0).

# Caso de uso (Use Case)

Desarrolladores que trabajan en IA Soberana, entrenan LLM y/o buscan mejorar la diversidad de los datos generados sintéticamente, mitigar sesgos de datos/modelos y prevenir el colapso de modelo.

–

Developers working on Sovereign AI, training LLMs, and/or looking to improve diversity of synthetically generated data, mitigate data/model biases, and prevent model collapse.

# Versión de los datos (Data Version)

1.0 (06/03/2026)

# Uso previsto (Intended Use)

El conjunto de datos Nemotron-Personas-El-Salvador está destinado a ser utilizado por la comunidad para seguir mejorando los modelos abiertos y hacer avanzar el estado del arte. Los datos pueden utilizarse libremente para entrenar cualquier modelo. Damos la bienvenida a los comentarios de la comunidad de código abierto e invitamos a desarrolladores, investigadores y entusiastas de los datos a explorar el conjunto de datos y construir a partir de él.

El conjunto de datos Nemotron-Personas-El-Salvador está anclado en distribuciones de datos demográficos autodeclarados del VII Censo de Población y VI Censo de Vivienda 2024, publicado por el Banco Central de Reserva de El Salvador (BCR) a través de su Oficina Nacional de Estadística y Censos (ONEC). Como tal, su objetivo principal es apoyar el desarrollo de IA Soberana combatiendo la falta de datos y/o los posibles sesgos presentes hoy en los datos de entrenamiento de modelos, especialmente en lo que respecta a los conjuntos de datos de personas existentes utilizados en la generación de datos sintéticos. A pesar de la mayor diversidad y fidelidad de los datos respecto a la población de El Salvador, todavía estamos limitados por la disponibilidad de los datos, su posible obsolescencia y una complejidad de modelo razonable. Esto da lugar a algunas suposiciones de independencia necesarias; por ejemplo, que las ocupaciones son independientes del nivel de educación, dado el departamento, la edad y el sexo.

Tenga en cuenta que el conjunto de datos se centra únicamente en adultos (18 años en adelante).

–

The Nemotron-Personas-El-Salvador dataset is intended to be used by the community to continue to improve open models and push the state of the art. The data may be freely used to train any model. We welcome feedback from the open-source community and invite developers, researchers, and data enthusiasts to explore the dataset and build upon it.

The Nemotron-Personas-El-Salvador dataset is grounded in distributions of self-reported demographic data from the VII Censo de Población y VI Censo de Vivienda 2024, published by the Banco Central de Reserva de El Salvador (BCR) through its Oficina Nacional de Estadística y Censos (ONEC). As such, its primary goal is to support Sovereign AI development by combating missing data and/or potential biases present in model training data today, especially when it comes to existing persona datasets used in synthetic data generation. Despite the improved data diversity and fidelity to El Salvador's population, we are still limited by data availability, current staleness of data, and reasonable model complexity. This results in some necessary independence assumptions; for instance, that occupations are independent of education degree, given the department, age and sex.

Note that the dataset is focused on adults only (ages 18 and above).

# Detalles del conjunto de datos (Dataset Details)

Esta versión contiene:

* **1M de personas** en español salvadoreño en **148.000 registros** (7 por registro)
* **300M de tokens**, incluyendo **161M de tokens de personas**
* 25 campos: 7 campos de persona y 18 campos contextuales (atributos de persona y datos demográficos) anclados en estadísticas oficiales
* Cobertura geográfica completa: los **14 departamentos** y **44 municipios** (tras la reorganización administrativa de 2024)
* **144k nombres únicos**
* Una estructura ocupacional anclada en el censo: **119 tipos de ocupación distintos** en **8 categorías de empleo** (EHPM 2024).
* Una variedad de tipos de persona: general, profesional, deportiva, artística, de viajes, culinaria, familiar

–

This release contains:

* **1M personas** in Salvadoran Spanish across **148k records** (7 per record)
* **300M tokens**, including **161M persona tokens**
* 25 fields: 7 persona fields and 18 contextual fields (persona attributes and demographics) grounded in official statistics
* Full geographic coverage: all **14 departamentos** and **44 municipios** (post-2024 administrative reorganization)
* **144k unique names**
* A census-grounded occupational structure: **119 distinct occupation types** across **8 employment categories** (EHPM 2024).
* A variety of persona types: general, professional, sports, arts, travel, culinary, family

## Datos semilla (Seed Data)

Para capturar la diversidad y la complejidad sociodemográfica y geográfica de la población de El Salvador, Nemotron-Personas-El-Salvador aprovechó los siguientes recursos:

* Datos del censo de población y vivienda publicados por el [Banco Central de Reserva de El Salvador (BCR)](https://www.bcr.gob.sv/) / [Oficina Nacional de Estadística y Censos (ONEC)](https://onec.bcr.gob.sv/), específicamente el [VII Censo de Población y VI Censo de Vivienda 2024](https://www.bcr.gob.sv/2024/10/31/bcr-presenta-resultados-del-vii-censo-de-poblacion-y-vi-censo-de-vivienda/) (6.029.976 personas) — el primer censo 100% digital del país, con la base de datos anonimizada disponible en el [geoportal del BCR](https://geoportal.bcr.gob.sv). Esto ancla el sexo, la edad, el departamento, el municipio, la educación, el estado civil/unión, la ocupación y (internamente) la etnicidad y el estatus urbano/rural.
* Distribuciones de frecuencia de nombres salvadoreños obtenidas del portal público de datos abiertos del [Registro Nacional de las Personas Naturales (RNPN)](https://www.rnpn.gob.sv/) (["Así Somos"](https://asisomos.rnpn.gob.sv)), construido a partir del registro civil del DUI, con un umbral de supresión por conteo de registros de N≥10. Las distribuciones finales de nombres utilizadas durante la generación se basan en \~5.377 nombres de pila únicos (2.194 masculinos / 3.188 femeninos) y \~2.036 apellidos únicos.

–

In order to capture the socio-demographic and geographic diversity and complexity of El Salvador's population, Nemotron-Personas-El-Salvador leveraged the following resources:

* Population and housing census data published by the [Banco Central de Reserva de El Salvador (BCR)](https://www.bcr.gob.sv/) / [Oficina Nacional de Estadística y Censos (ONEC)](https://onec.bcr.gob.sv/), specifically the [VII Censo de Población y VI Censo de Vivienda 2024](https://www.bcr.gob.sv/2024/10/31/bcr-presenta-resultados-del-vii-censo-de-poblacion-y-vi-censo-de-vivienda/) (6,029,976 persons) — the country's first 100% digital census, with the anonymized microdata available from the [BCR geoportal](https://geoportal.bcr.gob.sv). This grounds sex, age, department, municipality, education, marital/union status, occupation, and (internally) ethnicity and urban/rural status.
* Salvadoran name-frequency distributions obtained from the [Registro Nacional de las Personas Naturales (RNPN)](https://www.rnpn.gob.sv/) public open-data portal (["Así Somos"](https://asisomos.rnpn.gob.sv)), built from the DUI civil registry, with an N≥10 record-count suppression floor. Final name distributions used during generation draw on \~5,377 unique first names (2,194 male / 3,188 female) and \~2,036 unique surnames.

## Estructura de los datos (Schema)

El conjunto de datos incluye **25 campos**, compuestos por **7 campos de persona** y **18 campos contextuales**, como se muestra a continuación. El rico conjunto de atributos contextuales permite a los investigadores condicionar y orientar con precisión personas específicas, una capacidad difícil de lograr con los conjuntos de datos de personas existentes.

–

The dataset includes **25 fields**, comprising **7 persona fields** and **18 contextual fields**, as shown below. The rich set of contextual attributes enables researchers to precisely condition and target specific personas, a capability that is difficult to achieve with existing persona datasets.

| Field | Type | Description |
|-------|------|-------------|
| uuid | string | Globally unique identifier |
| professional_persona | string | Professional persona capturing primary field of work, key professional skills, traits and behavior |
| sports_persona | string | Sports persona describing athletic interests, sport team affiliations, and approach to fitness and exercise |
| arts_persona | string | Arts persona characterizing engagement with creative expression and how the arts shape their identity |
| travel_persona | string | Travel persona capturing travel interests and style |
| culinary_persona | string | Culinary persona describing food/cuisine preferences, cooking skill level, and approach to dining experiences |
| family_persona | string | Family persona describing household roles, relationships, and approach to family life |
| persona | string | A concise general-purpose persona capturing the essence of a person's perspective and approach to life |
| cultural_background | string | Description of the person's cultural background |
| skills_and_expertise | string | Professional and personal skills in narrative format |
| skills_and_expertise_list | string | List of skills and areas of expertise (JSON-encoded list) |
| hobbies_and_interests | string | Personal interests and recreational activities in narrative format |
| hobbies_and_interests_list | string | List of hobbies and personal interests (JSON-encoded list) |
| career_goals_and_ambitions | string | Professional aspirations and long-term career objectives |
| sex | string | Sex (Female, Male) |
| age | integer | Age in years (18–100) |
| languages_spoken | string | Languages spoken (CPV 2024 P12): `español`, `español e inglés`, `español y lengua indígena (náhuat, lenca o cacaopera)`, `español y otro idioma`, `lengua de señas salvadoreña (LESSA)`. Overwhelmingly `español`. Census-grounded. |
| marital_status | string | Relationship status: `soltero`, `casado`, `union_libre`, `divorciado`, `separado`, `viudo` |
| household_type | string | Household type: `unipersonal`, `pareja`, `nuclear`, `monoparental`, `extendido` |
| education_level | string | Highest level of education completed: `ninguno`, `primaria`, `secundaria`, `bachillerato`, `tecnico`, `universitario`, `posgrado` |
| occupation | string | Economic-activity class (CIIU Rev.4); 119 distinct types, e.g. `Actividades de hospitales`, `Cultivo de caña de azúcar`, `Construcción de edificios` |
| area | string | Area of residence: `urbano`, `rural` |
| municipality | string | Municipality of residence (one of 44; validated against department) |
| department | string | Department of residence (one of 14) |
| country | string | Country of residence (constant: "El Salvador") |

## Conteo de campos y tokens (Field & Token Counts)

\~300M de tokens (\~161M de tokens de personas) en 148.000 registros en español salvadoreño, a través de los 13 campos narrativos. El gráfico siguiente desglosa el total de tokens por campo narrativo.

–

\~300M tokens (\~161M persona tokens) across 148,000 records in Salvadoran Spanish, spanning the 13 narrative fields. The chart below breaks down total tokens per narrative field.

<center>
  <img src="images/nemotron_personas_el_salvador_field_stats.png" width="600px">
</center>

# Descripción del conjunto de datos y evaluación de la calidad (Dataset Description & Quality Assessment)

El análisis siguiente proporciona un desglose en varios ejes del conjunto de datos para resaltar la diversidad incorporada y la complejidad de los patrones de los datos.

–

The analysis below provides a breakdown across various axes of the dataset to emphasize the built-in diversity and pattern complexity of data.

## Nombres (Names)

Dado que el enfoque de este conjunto de datos está en las personas, los nombres no se proporcionan como campos dedicados. Sin embargo, en la generación de personas se infunden aproximadamente 5.377 nombres de pila únicos (2.194 masculinos / 3.188 femeninos) y 2.036 apellidos únicos obtenidos del portal de datos abiertos "Así Somos" del RNPN, tras un umbral de supresión por conteo de registros de N≥10 para protegerse contra la reidentificación.

Si bien se utilizan distribuciones de nombres realistas durante la generación de personas, los campos de nombres individuales no se exponen en el conjunto de datos final para reducir el riesgo de memorización y prevenir la reidentificación. La representatividad de los nombres recopilados se valida mediante una verificación cruzada externa contra los propios rankings de nombres publicados por el RNPN (solapamiento del top-10 ≥ 8/10 para masculinos, femeninos y apellidos). Dado que la fuente contabiliza registros de emisión del DUI en lugar de personas únicas, las frecuencias están ponderadas por emisión y la búsqueda de nombres de pila coincide con cualquier componente del nombre de pila (primer o segundo nombre); ambas propiedades son inherentes a la fuente y se divulgan en lugar de eliminarse artificialmente.

–

Since the focus of this dataset is on personas, names aren't provided as dedicated fields. However, infused into persona generation are approximately 5,377 unique first names (2,194 male / 3,188 female) and 2,036 unique surnames obtained from the RNPN "Así Somos" open-data portal, after an N≥10 record-count suppression floor to guard against re-identification.

While realistic name distributions are used during persona generation, individual name fields are not exposed in the final dataset to reduce memorization risk and prevent re-identification. The harvested names' representativeness is validated by an external cross-check against RNPN's own published name rankings (top-10 overlap ≥ 8/10 for male, female and surnames). Because the source counts DUI issuance records rather than unique persons, frequencies are issuance-weighted and the given-name search matches any given-name token (first or middle); both properties are inherent to the source and are disclosed rather than engineered away.

## Distribución por edad (Age Distribution)

Las personas se limitan a adultos salvadoreños (18–100 años). La distribución refleja la estructura demográfica real de El Salvador según lo reportado por el BCR/ONEC, con las mayores concentraciones entre los adultos jóvenes y en edad productiva, y una proporción progresivamente menor en las cohortes de mayor edad. De forma coherente con los datos censales, la representación femenina se vuelve ligeramente más prominente en los grupos de mayor edad, reflejando la mayor longevidad femenina. No se generan personas para menores de 18 años.

–

Personas are limited to adult Salvadorans (ages 18–100). The distribution mirrors El Salvador's real demographic structure as reported by BCR/ONEC, with the largest concentrations among young and prime working-age adults and a progressively smaller share in the older cohorts. Consistent with census data, female representation becomes slightly more prominent in older age groups, reflecting higher female longevity. No personas are generated for children under 18.

<center>
  <img src="images/nemotron_personas_el_salvador_age_distribution.png" width="700px">
</center>

<center>
  <img src="images/nemotron_personas_el_salvador_gender_pyramid.png" width="700px">
</center>

## Estado civil por grupo de edad (Marital Status by Age Group)

El mapa de calor siguiente muestra proporciones normalizadas por edad del estado civil en El Salvador. Los adultos más jóvenes son predominantemente solteros (`soltero`), con los estados de casado (`casado`) y unión libre (`union_libre`) en aumento a lo largo de los últimos veinte y los treinta años. Las uniones consensuales son una categoría culturalmente importante en El Salvador, representando una parte sustancial de las parejas, razón por la cual este conjunto de datos modela seis categorías de estado civil. La proporción de viudos (`viudo`) aumenta en las cohortes de mayor edad, mientras que los estados de divorciado/separado se mantienen comparativamente bajos en todas las edades.

–

The heatmap below shows age-normalized proportions of marital status in El Salvador. Younger adults are predominantly single (`soltero`), with married (`casado`) and consensual-union (`union_libre`) statuses rising through the late 20s and 30s. Consensual unions are a culturally important category in El Salvador, representing a substantial share of partnerships, which is why this dataset models six marital-status categories. The proportion of widowed (`viudo`) individuals rises in the oldest cohorts, while divorced/separated statuses remain comparatively low across all ages.

<center>
  <img src="images/nemotron_personas_el_salvador_marital_status_distribution.png" width="700px">
</center>

## Nivel de educación por grupo de edad (Education Level by Age Group)

Las distribuciones de educación están condicionadas a las cohortes de edad según lo reportado por el BCR/ONEC. Los datos capturan patrones de logro educativo a lo largo de las cohortes de edad, incluida la expansión de la educación secundaria y terciaria entre las generaciones más jóvenes y la mayor prevalencia de educación solo primaria o sin educación formal entre las cohortes de mayor edad.

–

Education distributions are conditioned on age cohorts as reported by BCR/ONEC. The data captures patterns of educational attainment across age cohorts, including the expansion of secondary and tertiary education among younger generations and the higher prevalence of primary-only or no-formal-education attainment among the oldest cohorts.

<center>
  <img src="images/nemotron_personas_el_salvador_education_distribution.png" width="700px">
</center>

## Particularidades geográficas del logro educativo (Geographic Intricacies of Education Attainment)

El logro educativo varía notablemente entre los 14 departamentos de El Salvador —reflejando la concentración del logro terciario en San Salvador y sus alrededores en relación con los departamentos más rurales—, lo que indica una heterogeneidad geográfica medible que los LLM por sí solos tienen dificultades para reproducir. Las personas están ancladas tanto a nivel de departamento como de municipio.

–

Educational attainment varies markedly across El Salvador's 14 departments — reflecting the concentration of tertiary attainment in and around San Salvador relative to more rural departments — indicating measurable geographic heterogeneity that LLMs alone struggle to reproduce. Personas are anchored at both the department and municipality level.

<center>
  <img src="images/nemotron_personas_el_salvador_education_map.png" width="700px">
</center>

## Categorías ocupacionales (Occupational Categories)

La estructura ocupacional está anclada en las estadísticas censales y laborales del BCR/ONEC (EHPM). El campo publicado `occupation` contiene **119 tipos de ocupación distintos** —clases de actividad económica CIIU Rev.4, p. ej. «Actividades de hospitales», «Cultivo de caña de azúcar» o «Construcción de edificios»— que abarcan las ocho categorías de empleo censales (empleado privado, empleado público, cuenta propia, empleador, otro empleado, trabajador doméstico, trabajador familiar no remunerado y no especificado). Esto refleja la estructura del mercado laboral salvadoreño, incluido un sector informal y de cuenta propia sustancial. El detalle ocupacional más rico se expresa en las narrativas de persona en lenguaje natural.

–

The occupational structure is grounded in BCR/ONEC census and EHPM labor statistics. The published `occupation` field contains **119 distinct occupation types** — CIIU Rev.4 economic-activity classes, e.g. "Actividades de hospitales", "Cultivo de caña de azúcar", or "Construcción de edificios" — spanning the eight census employment categories (private employee, public employee, own-account worker, employer, other employee, domestic worker, unpaid family worker, and unspecified). This reflects the structure of the Salvadoran labor market, including a substantial informal and own-account sector. Richer occupational detail is expressed in the natural-language persona narratives.

<center>
  <img src="images/nemotron_personas_el_salvador_occupation.png" width="700px">
</center>

## Diversidad de personas (Persona Diversity)

Los atributos anteriores (y muchos otros) afectan, en última instancia, la diversidad de las personas sintéticas generadas. Como ejemplo, el análisis siguiente destaca una multitud de agrupaciones (*clusters*) dentro de las descripciones de personas profesionales. Estos *clusters* se identifican agrupando *embeddings* y reduciendo la dimensionalidad a 2D.

–

The attributes above (and many more) ultimately affect the diversity of the synthetic personas being generated. As an example, the analysis below highlights a multitude of clusters within professional persona descriptions. These clusters are identified by clustering embeddings and reducing dimensionality to 2D.

<center>
  <img src="images/nemotron_personas_el_salvador_persona_diversity.png" width="600px">
</center>

# Cómo usarlo (How to use it)

Puede cargar el conjunto de datos con las siguientes líneas de código.

–

You can load the dataset with the following lines of code.

```python
from datasets import load_dataset

# Personas en español salvadoreño / Salvadoran Spanish personas
nemotron_personas = load_dataset("nvidia/Nemotron-Personas-El-Salvador")
```

# Caracterización del conjunto de datos (Dataset Characterization)

## Método de recolección de datos (Data Collection Method)
* Híbrido (Humano, Sintético, Automatizado) / Hybrid (Human, Synthetic, Automated)

## Método de etiquetado (Labeling Method)
* No aplicable / Not Applicable

## Formato del conjunto de datos (Dataset Format)
* Parquet (cadenas y enteros; esquema completo en la sección "Estructura de los datos (Schema)") / Parquet (strings and integers; full schema in the "Schema" section)

## Cuantificación del conjunto de datos (Dataset Quantification)
* Conteo de registros (Record counts): 148.000 registros (\~1M de personas, 7 por registro)
* Conteo de tokens (Token counts): \~300M de tokens en total (\~161M de tokens de personas)
* Almacenamiento total (Total data storage): \~542 MB (Parquet, compresión snappy / snappy compression)

# Consideraciones éticas (Ethical Considerations)

NVIDIA cree que la [IA Confiable](https://www.nvidia.com/en-us/ai-data-science/trustworthy-ai/) es una responsabilidad compartida y hemos establecido políticas y prácticas para permitir el desarrollo de una amplia gama de aplicaciones de IA. Al descargar o usar de acuerdo con nuestros términos de servicio, los desarrolladores deben trabajar con sus equipos internos para garantizar que este conjunto de datos cumpla con los requisitos para la industria y el caso de uso relevantes y aborde el uso indebido imprevisto del producto.

Este conjunto de datos no contiene información de identificación personal. Si bien se utilizan distribuciones del mundo real de edades, nombres y ocupaciones de fuentes públicas oficiales, nada está vinculado a ninguna persona real, viva o fallecida. Cada persona es completamente sintética por diseño.

Las limitaciones conocidas documentadas para esta publicación incluyen: subrepresentación de las identidades indígenas (Náhuat-Pipil, Lenca, Kakawira) y afrodescendientes (poblaciones pequeñas combinadas con la supresión de celdas pequeñas); supuestos sobre roles de género que pueden heredarse del LLM narrativo a pesar del condicionamiento demográfico equilibrado; y un español salvadoreño que es aproximado por el modelo generativo en lugar de extraerse de un corpus NLP salvadoreño autorizado. La religión no se modela en esta versión.

Por favor, reporte problemas de calidad, riesgo, vulnerabilidades de seguridad o preocupaciones de IA de NVIDIA [aquí](https://www.nvidia.com/en-us/support/submit-security-vulnerability/).

–

NVIDIA believes [Trustworthy AI](https://www.nvidia.com/en-us/ai-data-science/trustworthy-ai/) is a shared responsibility and we have established policies and practices to enable development for a wide array of AI applications. When downloaded or used in accordance with our terms of service, developers should work with their internal teams to ensure this dataset meets requirements for the relevant industry and use case and addresses unforeseen product misuse.

This dataset contains no personally identifiable information. While real-world distributions of ages, names, and occupations from official public sources are used, nothing is tied to any real person, living or deceased. Every persona is fully synthetic by design.

Known limitations documented for this release include: under-representation of Indigenous (Náhuat-Pipil, Lenca, Kakawira) and Afrodescendant identities (small populations combined with small-cell suppression); gender-role assumptions that may be inherited from the narrative LLM despite balanced demographic conditioning; and Salvadoran Spanish dialect that is approximated by the generative model rather than drawn from an authoritative Salvadoran NLP corpus. Religion is not modeled in this version.

Please report quality, risk, security vulnerabilities or NVIDIA AI Concerns [here](https://www.nvidia.com/en-us/support/submit-security-vulnerability/).

# Cita (Citation)

Si encuentra útiles los datos, por favor cite (If you find the data useful, please cite):

```
@software{nvidia/Nemotron-Personas-El-Salvador,
 author = {Malossi, Rodrigo and Manoel, Andre and Prayaga, Shyamala and Sharabiani, Ashton and Acharya, Evan and Sadeghi, Bardiya and Jennings, Will and Praveen, Kiran and Corneil, Dane and Meyer, Yev},
 title = {{Nemotron-Personas-El-Salvador: Synthetic Personas Aligned to Real-World Distributions for El Salvador}},
 year = {2026},
 url = {https://huggingface.co/datasets/nvidia/Nemotron-Personas-El-Salvador}
}
```
