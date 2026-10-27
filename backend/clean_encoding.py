import re
import sqlite3

EXACT_REPLACEMENTS = [
    # Complex / multi-character sequences
    ('Amphith\ufffd\ufffdtre', 'Amphithéâtre'),
    ('Amphith\ufffdtre', 'Amphithéâtre'),
    ('Amphith??tre', 'Amphithéâtre'),
    ('Amphith?tre', 'Amphithéâtre'),
    ('\ufffd\ufffd', 'éâ'),
    
    # Specific expressions
    ('Mise en \ufffduvre', 'Mise en œuvre'),
    ('\ufffduvre', 'œuvre'),
    ('Cr\ufffdation\ufffd et mise', 'Création et mise'),
    ('Projet\ufffd:', 'Projet :'),
    ('Transferts\ufffdthermiques', 'Transferts thermiques'),
    ('M\ufffdcanique\ufffddes\ufffdFluides', 'Mécanique des Fluides'),
    ('D\ufffdveloppement\ufffdweb', 'Développement web'),
    
    # Specific words with accents
    ('Fai\ufffdal', 'Faïçal'),
    ('Co\ufffdts', 'Coûts'),
    ('co\ufffdt', 'coût'),
    ('co\ufffdts', 'coûts'),
    ('Cha\ufffdne', 'Chaîne'),
    ('cha\ufffdne', 'chaîne'),
    ('fran\ufffdais', 'français'),
    ('Fran\ufffdais', 'Français'),
    ('v\ufffdtements', 'vêtements'),
    ('V\ufffdtements', 'Vêtements'),
    ('S\ufffdret\ufffd', 'Sûreté'),
    ('s\ufffdret\ufffd', 'sûreté'),
    ('Contr\ufffdle', 'Contrôle'),
    ('contr\ufffdle', 'contrôle'),
    ('Syst\ufffdme', 'Système'),
    ('syst\ufffdme', 'système'),
    ('probl\ufffdmes', 'problèmes'),
    ('Probl\ufffdmes', 'Problèmes'),
    ('polym\ufffdres', 'polymères'),
    ('Mati\ufffdre', 'Matière'),
    ('mati\ufffdre', 'matière'),
    ('Mati\ufffdres', 'Matières'),
    ('mati\ufffdres', 'matières'),
    ('multicrit\ufffdre', 'multicritère'),
    ('Hygi\ufffdne', 'Hygiène'),
    ('inh\ufffdrents', 'inhérents'),
    ('inh\ufffdrente', 'inhérente'),
    ('mod\ufffdlisme', 'modélisme'),
    ('D\ufffdlavage', 'Délavage'),
    ('M\ufffdtrologie', 'Métrologie'),
    ('m\ufffdtrologie', 'métrologie'),
    ('TP \ufffdlectronique', 'TP Électronique'),
    ('et \ufffdlectrotechnique', 'et Électrotechnique'),
    ('Electronique Appliqu\ufffde', 'Électronique Appliquée'),
    ('D\ufffdveloppement', 'Développement'),
    ('d\ufffdveloppement', 'développement'),
    ('D\ufffdcision', 'Décision'),
    ('d\ufffdcision', 'décision'),
    ('D\ufffdcarbonation', 'Décarbonation'),
    ('d\ufffdcarbonation', 'décarbonation'),
    ('Mastiere', 'Mastère'),
    
    # Prepositions with \ufffd
    ('\ufffd la ', 'à la '),
    (' \ufffd la', ' à la'),
    (' \ufffd l\'', ' à l\''),
    (' \ufffd ', ' à '),
    
    # General vocabulary
    ('qualit\ufffd', 'qualité'),
    ('Qualit\ufffd', 'Qualité'),
    ('strat\ufffdgie', 'stratégie'),
    ('Strat\ufffdgie', 'Stratégie'),
    ('strat\ufffdgique', 'stratégique'),
    ('Strat\ufffdgique', 'Stratégique'),
    ('Math\ufffdmatique', 'Mathématique'),
    ('appliqu\ufffd', 'appliqué'),
    ('Appliqu\ufffd', 'Appliqué'),
    ('Avanc\ufffd', 'Avancé'),
    ('avanc\ufffd', 'avancé'),
    ('Interpr\ufffdtation', 'Interprétation'),
    ('N\ufffdgociation', 'Négociation'),
    ('n\ufffdgociation', 'négociation'),
    ('Comptabilit\ufffd', 'Comptabilité'),
    ('g\ufffdn\ufffdral', 'général'),
    ('G\ufffdn\ufffdral', 'Général'),
    ('M\ufffdcanique', 'Mécanique'),
    ('m\ufffdcanique', 'mécanique'),
    ('R\ufffdalisation', 'Réalisation'),
    ('r\ufffdalisation', 'réalisation'),
    ('op\ufffdration', 'opération'),
    ('Op\ufffdration', 'Opération'),
    ('r\ufffdsolution', 'résolution'),
    ('Donn\ufffd', 'Donné'),
    ('donn\ufffd', 'donné'),
    ('Mat\ufffdriau', 'Matériau'),
    ('mat\ufffdriau', 'matériau'),
    ('\ufffdquilibrage', 'équilibrage'),
    ('cr\ufffdation', 'création'),
    ('Cr\ufffdation', 'Création'),
    ('exp\ufffddition', 'expédition'),
    ('\ufffdvaluation', 'Évaluation'),
    ('Assist\ufffd', 'Assisté'),
    ('assist\ufffd', 'assisté'),
    ('\ufffdquipement', 'équipement'),
    ('int\ufffdgr', 'intégr'),
    ('\ufffdconomie', 'Économie'),
    ('G\ufffdopolitique', 'Géopolitique'),
    ('\ufffdtendue', 'étendue'),
    ('m\ufffdtier', 'métier'),
    ('M\ufffdtier', 'Métier'),
    ('S\ufffdlection', 'Sélection'),
    ('s\ufffdlection', 'sélection'),
    ('\ufffdnerg', 'énerg'),
    ('proc\ufffd', 'procé'),
    ('V\ufffdrification', 'Vérification'),
    ('v\ufffdrification', 'vérification'),
    ('Cybers\ufffdcurit\ufffd', 'Cybersécurité'),
    ('Propri\ufffdt\ufffd', 'Propriété'),
    ('propri\ufffdt\ufffd', 'propriété'),
    ('R\ufffdglement', 'Réglement'),
    ('r\ufffdglement', 'réglement'),
    ('Mod\ufffdlisation', 'Modélisation'),
    ('mod\ufffdlisation', 'modélisation'),
    ('\ufffdco-responsable', 'éco-responsable'),
    ('March\ufffd', 'Marché'),
    ('march\ufffd', 'marché'),
    ('m\ufffdthode', 'méthode'),
    ('M\ufffdthode', 'Méthode'),
    ('R\ufffdsistance', 'Résistance'),
    ('r\ufffdsistance', 'résistance'),
    ('Orient\ufffd', 'Orienté'),
    ('orient\ufffd', 'orienté'),
    ('\ufffdlectr', 'électr'),
    ('Electr', 'Électr'),
    ('visite dentreprise', "visite d'entreprise"),
    ('viste dentreprise', "visite d'entreprise"),
]

def sanitize_string(s):
    if not s or not isinstance(s, str):
        return s
    
    # 1. First fix apostrophes like lentreprise, dun, LHistoire
    s = re.sub(r'(?<=\b[ldLD])\ufffd(?=[a-zA-Z\u00c0-\u00ff])', "'", s)
    
    # 2. Exact word replacements
    for old, new in EXACT_REPLACEMENTS:
        s = s.replace(old, new)
        
    # 3. Handle any literal question marks in Amphith?tre
    s = re.sub(r'Amphith[?]+\s*tre', 'Amphithéâtre', s, flags=re.IGNORECASE)
    
    # 4. Fallback for any single remaining \ufffd
    s = s.replace('\ufffd', 'é')
    
    return s


def run_fix():
    db_path = "hall_esith_v3.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    tables = ['cours', 'formations', 'events', 'absences', 'retards', 'changement_salle']
    total_updated = 0
    
    for table in tables:
        try:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [r[1] for r in cursor.fetchall() if r[2] in ('TEXT', 'VARCHAR', '')]
            
            for col in columns:
                cursor.execute(f"SELECT id, {col} FROM {table} WHERE {col} IS NOT NULL AND instr({col}, char(65533)) > 0")
                rows = cursor.fetchall()
                for row_id, val in rows:
                    new_val = sanitize_string(val)
                    if new_val != val:
                        cursor.execute(f"UPDATE {table} SET {col} = ? WHERE id = ?", (new_val, row_id))
                        total_updated += 1
                        
                # Also check for any 'Amphith?tre' with literal question marks
                cursor.execute(f"SELECT id, {col} FROM {table} WHERE {col} LIKE '%Amphith%tre%'")
                for row_id, val in cursor.fetchall():
                    new_val = sanitize_string(val)
                    if new_val != val:
                        cursor.execute(f"UPDATE {table} SET {col} = ? WHERE id = ?", (new_val, row_id))
                        total_updated += 1
        except Exception as e:
            print(f"Error on {table}: {e}")
            
    conn.commit()
    conn.close()
    print(f"Database sanitized successfully. Total fields updated: {total_updated}")


if __name__ == '__main__':
    run_fix()
