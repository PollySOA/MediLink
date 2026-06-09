from models.schemas import FictionalPatient

FICTIONAL_PATIENTS: list[FictionalPatient] = [
    FictionalPatient(
        id="PAT-001",
        name="Carmen Rodríguez Vega",
        dni="11111111A",
        age=58,
        gender="female",
        conditions=["hipertensión arterial", "dislipemia"],
        specialty="medicina interna",
        assigned_doctor_id="DOC-002",
        sample_report=(
            "Radiografía de tórax PA y lateral. Índice cardiotorácico en el límite "
            "alto de la normalidad (0.52). Hilios vasculares de morfología normal. "
            "Senos costofrénicos libres. Parénquima pulmonar sin condensaciones. "
            "Aorta elongada con calcificaciones en cayado. "
            "Conclusión: Cardiomegalia leve límite. Cambios ateromatosos aórticos. "
            "Sin signos de insuficiencia cardíaca congestiva."
        ),
        clinical_context="Control anual. Hipertensa con tratamiento desde hace 10 años.",
    ),
    FictionalPatient(
        id="PAT-002",
        name="Carolina Riera Segura",
        dni="D210105597",
        age=67,
        gender="female",
        conditions=["dolor de rodilla", "limitacion funcional al caminar por terreno irregular"],
        specialty="traumatología",
        assigned_doctor_id="DOC-001",
        sample_report=(
            "RM de rodilla. Articulación fémoropatelar con patela alta "
            "(índice IS de 1,5) con fisuras grado II-III en faceta patelar externa. "
            "No se observa derrame articular. Meniscos y ligamentos completamente sanos. "
            "Conclusión: cambios femoropatelares compatibles con sobrecarga patelar, sin lesión meniscal ni ligamentosa."
        ),
        clinical_context="Dolor de rodilla con dificultad para caminar por la montaña. Caso guiado para Avatar Elena.",
    ),
    FictionalPatient(
        id="PAT-003",
        name="Rosa Elena Fuentes",
        dni="33333333C",
        age=72,
        gender="female",
        conditions=["diabetes tipo 2", "EPOC leve", "ex-fumadora"],
        specialty="neumología",
        assigned_doctor_id="DOC-002",
        sample_report=(
            "TC de tórax de baja dosis para screening. "
            "Nódulo sólido en lóbulo superior derecho de 8mm, bordes espiculados, "
            "sin cambios respecto a TC previo de hace 6 meses. "
            "Enfisema centrilobulillar leve bilateral de predominio en lóbulos superiores. "
            "No se identifican adenopatías mediastínicas. "
            "Conclusión: Nódulo pulmonar estable. Categoría Lung-RADS 3. "
            "Seguimiento con TC en 6 meses."
        ),
        clinical_context="Exfumadora de 30 paquetes/año. Programa de seguimiento de nódulo.",
    ),
    FictionalPatient(
        id="PAT-004",
        name="Miguel Ángel Domínguez",
        dni="44444444D",
        age=45,
        gender="male",
        conditions=["sin antecedentes relevantes"],
        specialty="cardiología",
        assigned_doctor_id="DOC-002",
        sample_report=(
            "Ecocardiograma transtorácico. Ventrículo izquierdo no dilatado con "
            "función sistólica conservada, fracción de eyección 62%. "
            "Válvula aórtica trivalva calcificada con área valvular 1.4 cm², "
            "gradiente medio 18mmHg, estenosis leve-moderada. "
            "Conclusión: Estenosis aórtica leve-moderada. Seguimiento anual."
        ),
        clinical_context="Hallazgo incidental en revisión médica. Soplo sistólico.",
    ),
    FictionalPatient(
        id="PAT-005",
        name="Isabel Méndez Ruiz",
        dni="55555555E",
        age=29,
        gender="female",
        conditions=["migrañas crónicas"],
        specialty="neurología",
        assigned_doctor_id="DOC-002",
        sample_report=(
            "RM craneal sin contraste. Estudio dentro de límites normales. "
            "No se identifican lesiones focales isquémicas ni hemorrágicas. "
            "Sistema ventricular de tamaño y morfología normales. "
            "Conclusión: RM craneal sin hallazgos patológicos relevantes."
        ),
        clinical_context="Cefaleas recurrentes desde hace 3 años. Estudio de despistaje.",
    ),
]

PATIENT_MAP: dict[str, FictionalPatient] = {p.id: p for p in FICTIONAL_PATIENTS}
