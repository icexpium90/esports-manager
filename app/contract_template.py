"""Modèle de contrat joueur par jeu.

Le texte reprend la trame d'un contrat de joueur esport d'association. Les variables entre accolades
sont remplacées à la génération :
  {structure} {tag} {jeu} {editeur} {duree} {date_debut}
Mise en forme : une ligne « ARTICLE n — Titre » devient un bandeau de section ; « a) », « b) »… et « • » sont des
retraits ; une ligne vide sépare les paragraphes.
"""

GAME_INFO = {
    "cs2": {
        "code": "CS2",
        "editeur": "Valve Corporation",
        "plateforme": "PC — Steam (plateforme principale compétitive)",
        "roster": "5 joueurs titulaires et 1 à 2 remplaçants",
        "rang": "Le Joueur devra justifier d'un rang minimum de Master Guardian Elite (MGE) ou équivalent sur la "
                "plateforme compétitive de référence (matchmaking Valve, FACEIT, ESEA).",
        "pratique_libre": "la pratique en matchmaking, en parties personnalisées ou sur FACEIT à titre individuel ;",
        "specifique": """a) Le Joueur participe aux sessions d'entraînement collectif selon un planning établi en concertation avec le coach ou l'IGL, compte tenu de ses obligations scolaires, professionnelles et personnelles.
b) Le rôle principal du Joueur (AWPer, Rifler, Entry Fragger, Lurker, Support, IGL) est défini d'un commun accord avec le staff. Le Joueur peut être amené à occuper ponctuellement un autre rôle selon les besoins de l'équipe.
c) Le Joueur se rend disponible, dans la mesure du possible, pour les matchs de ligue et les tournois auxquels l'équipe est inscrite. Toute indisponibilité est signalée au staff dans les meilleurs délais.
d) Le Joueur participe aux séances d'analyse de démos organisées par le coach.
e) Le Joueur entretient son niveau de jeu individuel et se tient informé des mises à jour et évolutions de la méta.
f) Le Joueur maîtrise l'usage des utilitaires (smokes, flashbangs, molotovs, grenades HE) sur les cartes du map pool de l'équipe.""",
    },
    "valorant": {
        "code": "VAL",
        "editeur": "Riot Games",
        "plateforme": "PC — Riot Client",
        "roster": "5 joueurs titulaires et 1 à 2 remplaçants",
        "rang": "Le Joueur devra justifier d'un rang minimum défini par le staff sportif sur le mode classé de "
                "Valorant ou une plateforme compétitive équivalente.",
        "pratique_libre": "la pratique en parties classées, non classées ou personnalisées à titre individuel ;",
        "specifique": """a) Le Joueur participe aux sessions d'entraînement collectif selon un planning établi en concertation avec le coach ou l'IGL, compte tenu de ses obligations scolaires, professionnelles et personnelles.
b) Le rôle principal du Joueur (Duelist, Initiator, Controller, Sentinel, IGL) et son pool d'agents sont définis d'un commun accord avec le staff. Le Joueur peut être amené à occuper ponctuellement un autre rôle selon les besoins de l'équipe.
c) Le Joueur se rend disponible, dans la mesure du possible, pour les matchs de ligue et les tournois auxquels l'équipe est inscrite. Toute indisponibilité est signalée au staff dans les meilleurs délais.
d) Le Joueur participe aux séances d'analyse de VOD organisées par le coach.
e) Le Joueur entretient son niveau de jeu individuel et se tient informé des mises à jour et évolutions de la méta.
f) Le Joueur maîtrise les line-ups et l'usage des compétences sur les cartes du map pool de l'équipe.""",
    },
    "r6": {
        "code": "R6",
        "editeur": "Ubisoft",
        "plateforme": "PC — Ubisoft Connect",
        "roster": "5 joueurs titulaires et 1 à 2 remplaçants",
        "rang": "Le Joueur devra justifier d'un rang minimum défini par le staff sportif sur le mode classé de "
                "Rainbow Six Siege ou une plateforme compétitive équivalente.",
        "pratique_libre": "la pratique en parties classées, non classées ou personnalisées à titre individuel ;",
        "specifique": """a) Le Joueur participe aux sessions d'entraînement collectif selon un planning établi en concertation avec le coach ou l'IGL, compte tenu de ses obligations scolaires, professionnelles et personnelles.
b) Le rôle principal du Joueur (Entry, Support, Flex, Anchor, Roamer, IGL) et son pool d'opérateurs sont définis d'un commun accord avec le staff. Le Joueur peut être amené à occuper ponctuellement un autre rôle selon les besoins de l'équipe.
c) Le Joueur se rend disponible, dans la mesure du possible, pour les matchs de ligue et les tournois auxquels l'équipe est inscrite. Toute indisponibilité est signalée au staff dans les meilleurs délais.
d) Le Joueur participe aux séances d'analyse de replays organisées par le coach.
e) Le Joueur entretient son niveau de jeu individuel et se tient informé des mises à jour et évolutions de la méta.
f) Le Joueur maîtrise les renforts, les gadgets et l'usage des drones sur les cartes du map pool de l'équipe.""",
    },
    "rocket_league": {
        "code": "RL",
        "editeur": "Psyonix",
        "plateforme": "PC — Epic Games / Steam",
        "roster": "3 joueurs titulaires et 1 remplaçant",
        "rang": "Le Joueur devra justifier d'un rang minimum défini par le staff sportif sur le mode classé de "
                "Rocket League.",
        "pratique_libre": "la pratique en parties classées, occasionnelles ou privées à titre individuel ;",
        "specifique": """a) Le Joueur participe aux sessions d'entraînement collectif selon un planning établi en concertation avec le coach ou le capitaine, compte tenu de ses obligations scolaires, professionnelles et personnelles.
b) Le rôle du Joueur dans les rotations est défini d'un commun accord avec le staff.
c) Le Joueur se rend disponible, dans la mesure du possible, pour les matchs de ligue et les tournois auxquels l'équipe est inscrite. Toute indisponibilité est signalée au staff dans les meilleurs délais.
d) Le Joueur participe aux séances d'analyse de replays organisées par le coach.
e) Le Joueur entretient son niveau mécanique individuel (training packs, free play) et se tient informé des mises à jour du jeu.""",
    },
}

BASE = """ARTICLE 1 — Objet du contrat
1.1. Le présent Contrat a pour objet de définir les conditions dans lesquelles le Joueur rejoint la division {jeu} de la structure esportive {structure} en tant que joueur compétitif, ainsi que les droits et obligations réciproques des Parties.
1.2. Le Joueur s'engage à représenter l'Association dans le cadre des compétitions, événements, entraînements et activités promotionnelles liées au jeu {jeu} (édité par {editeur}), selon les modalités définies ci-après.
1.3. Le Joueur reconnaît avoir pris connaissance du règlement intérieur de l'Association et s'engage à le respecter.

ARTICLE 2 — Durée du contrat
2.1. Le présent Contrat est conclu {duree}.
2.2. Chaque Partie pourra mettre fin au Contrat à tout moment, sous réserve du respect d'un préavis de trente (30) jours, notifié par écrit (e-mail ou courrier recommandé).
2.3. À l'expiration du préavis, le Contrat prendra fin de plein droit, sans qu'aucune indemnité ne soit due de part et d'autre, sous réserve des obligations subsistant après la fin du Contrat (confidentialité, droit à l'image).

ARTICLE 3 — Composition de l'équipe {jeu}
3.1. L'équipe {jeu} de {structure} est composée de @roster@.
3.2. La composition de l'équipe (roster) est définie par le staff sportif (coach, manager, direction sportive). Le Joueur accepte que sa position de titulaire puisse être remise en question selon ses performances et son investissement.
3.3. @rang@

ARTICLE 4 — Engagements du joueur
4.1. Engagements généraux
a) Le Joueur représente {structure} avec professionnalisme et fair-play lors des compétitions, entraînements et événements auxquels il participe au nom de l'Association.
b) Le Joueur s'abstient de tout propos discriminatoire, raciste, sexiste ou injurieux, en ligne comme hors ligne, susceptible de porter atteinte à l'image de l'Association. Tout différend à ce sujet fait l'objet d'un entretien préalable entre le Joueur et la direction.
c) L'utilisation de logiciels de triche, d'exploits, de macros ou de tout outil interdit par l'éditeur ou les organisateurs de tournois est proscrite. Tout manquement avéré peut entraîner la résiliation du Contrat, après que le Joueur a été entendu.
d) Le Joueur assure la bonne conservation du matériel mis à sa disposition et le restitue à l'issue du Contrat, sous réserve de l'usure normale.
4.2. Engagements sportifs — {jeu}
@specifique@
4.3. Communication et image
a) Le Joueur autorise l'Association à utiliser son pseudonyme, son image et sa voix dans le cadre de ses communications et contenus médias. Le Joueur peut solliciter, par demande motivée, le retrait d'un contenu le concernant.
b) Le Joueur affiche le tag « {tag} » ou « {structure_court} » devant son pseudonyme sur les plateformes compétitives pendant la durée du Contrat.
c) Le Joueur porte la tenue officielle fournie par l'Association lors des événements et compétitions en LAN.
4.4. Exclusivité — Pendant la durée du Contrat, le Joueur s'engage à ne pas représenter une autre structure esportive sur {jeu} sans l'accord préalable de l'Association. Ne sont pas soumises à cet accord :
• @pratique_libre@
• la pratique d'autres jeux ;
• la participation à des compétitions ou activités organisées dans le cadre d'une école spécialisée dans l'événementiel jeu vidéo ou d'une académie esport (de type GS Esport School), sous réserve que celles-ci n'entrent pas en conflit avec un match officiel de {structure}.

ARTICLE 5 — Obligations de l'Association
5.1. L'Association s'engage à fournir au Joueur un cadre structuré pour la pratique compétitive : encadrement sportif (coach, manager), accès aux outils de communication d'équipe (Discord, serveur d'entraînement) et inscription aux compétitions.
5.2. L'Association s'engage à inscrire le Joueur aux compétitions et tournois correspondant au niveau de l'équipe {jeu}.
5.3. L'Association s'engage à traiter le Joueur avec respect et dignité, et à veiller au bien-être de ses membres.
5.4. L'Association pourra, selon ses moyens, prendre en charge tout ou partie des frais liés aux compétitions (frais d'inscription, déplacements, hébergement). Les conditions de prise en charge seront précisées par avenant ou note interne.
5.5. L'Association s'engage à fournir au Joueur les équipements aux couleurs de la structure (maillot, merchandising) dans la mesure de ses disponibilités.

ARTICLE 6 — Conditions financières
6.1. Le présent Contrat étant conclu dans le cadre d'une ASBL, le Joueur ne perçoit aucune rémunération salariale.
6.2. Répartition des gains — En cas de gains issus de compétitions ou tournois sur {jeu}, la répartition s'effectuera comme suit :
• 25 % du cashprize par tournoi pour le Joueur de la division ;
• 25 % pour l'Association lors des événements de Gamers Assembly (réinvestissement dans la structure).
6.3. Remboursements — Les frais engagés par le Joueur pour le compte de l'Association pourront faire l'objet d'un remboursement sur présentation de justificatifs et après validation préalable par le bureau.
6.4. Sponsoring — Les éventuels revenus issus de partenariats ou sponsors liés à la division seront gérés par l'Association, qui en informera les joueurs.

ARTICLE 7 — Propriété intellectuelle et droit à l'image
7.1. Le Joueur autorise l'Association à utiliser, reproduire et diffuser son image, son pseudonyme, sa voix et ses performances dans le cadre des activités promotionnelles de {structure}, sur tous supports (site web, réseaux sociaux, streaming, presse).
7.2. Cette autorisation est accordée pour la durée du Contrat et pendant six (6) mois suivant sa fin, sauf opposition écrite du Joueur.
7.3. Le Joueur conserve la propriété de son pseudonyme (gamertag) et de ses comptes personnels de jeu.
7.4. Les contenus créés conjointement (vidéos, streams, contenus éditoriaux) restent la propriété de l'Association, sauf accord contraire écrit.

ARTICLE 8 — Confidentialité
8.1. Le Joueur s'engage à ne divulguer aucune information confidentielle relative à l'organisation interne de l'Association, aux stratégies de jeu de la division {jeu}, aux projets en cours ou aux données financières.
8.2. Cette obligation demeure pendant toute la durée du Contrat et douze (12) mois après sa cessation.

ARTICLE 9 — Résiliation
9.1. Résiliation d'un commun accord — Le Contrat peut être résilié à tout moment par accord écrit des deux Parties.
9.2. Résiliation par le Joueur — Préavis de trente (30) jours, notifié par écrit.
9.3. Résiliation par l'Association — L'Association peut résilier le Contrat sans préavis en cas de :
a) manquement grave ou répété aux obligations du Joueur ;
b) comportement portant atteinte à l'image de l'Association ;
c) inactivité prolongée sans justification (plus de 30 jours consécutifs) ;
d) utilisation avérée de logiciels de triche ou de tout outil interdit ;
e) violation de la clause de confidentialité ou d'exclusivité.
9.4. En cas de résiliation pour faute, le Joueur disposera de quinze (15) jours pour formuler des observations.

ARTICLE 10 — Protection des données personnelles
10.1. Conformément au RGPD (Règlement UE 2016/679), l'Association s'engage à traiter les données personnelles du Joueur avec confidentialité et uniquement aux fins de gestion administrative et sportive.
10.2. Le Joueur dispose d'un droit d'accès, de rectification, de portabilité et de suppression de ses données.
10.3. Les données personnelles ne seront en aucun cas cédées à des tiers sans consentement préalable, sauf obligation légale.

ARTICLE 11 — Dispositions relatives aux joueurs mineurs
11.1. Si le Joueur est mineur, le Contrat devra être cosigné par son représentant légal (parent ou tuteur).
11.2. L'Association s'engage à respecter les règles de protection des mineurs (horaires de pratique, durée des sessions, participation aux événements).
11.3. Le représentant légal pourra, à tout moment, demander la résiliation du Contrat par écrit et sans préavis.

ARTICLE 12 — Règlement des litiges
12.1. En cas de différend, les Parties s'engagent à rechercher une solution amiable.
12.2. À défaut de résolution amiable dans un délai de trente (30) jours, le litige sera soumis aux juridictions du Grand-Duché de Luxembourg.
12.3. Le présent Contrat est régi par le droit luxembourgeois.

ARTICLE 13 — Dispositions générales
13.1. Le présent Contrat constitue l'intégralité de l'accord entre les Parties et annule tout accord antérieur portant sur le même objet.
13.2. Toute modification devra faire l'objet d'un avenant écrit signé par les deux Parties.
13.3. Si l'une des clauses était déclarée nulle, les autres resteraient pleinement en vigueur.
13.4. Les notifications pourront être faites par e-mail ou courrier à l'adresse du siège social."""


def default_clauses(game: str) -> str:
    g = GAME_INFO.get(game, GAME_INFO["cs2"])
    return (BASE.replace("@roster@", g["roster"]).replace("@rang@", g["rang"])
            .replace("@specifique@", g["specifique"]).replace("@pratique_libre@", g["pratique_libre"]))


def fill(text: str, values: dict) -> str:
    """Remplace uniquement les variables connues (les autres accolades restent intactes)."""
    for key, value in values.items():
        text = text.replace("{" + key + "}", value)
    return text
