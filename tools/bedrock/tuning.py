"""
Ajustes finos de colocacion del arma en Bedrock.

La posicion en primera persona se calcula a partir de la pose vanilla del brazo
(animation.player.first_person.empty_hand). Si en tu version el arma aparece algo
desplazada, corrige estos valores y vuelve a ejecutar build_bedrock.py.
Unidades: pixeles de modelo (1 bloque = 16 / 0.9375 px).
"""

FP_TUNING = {
    # altura del ojo sobre los pies en px de modelo (1.62 bloques / 0.9375 * 16)
    "eye_height_px": 27.65,
}

TP_TUNING = {
    # pose del brazo derecho que aplica animation.fps.player.aim en tercera persona (valores Bedrock)
    "arm_rot": (-90.0, -5.0, 0.0),
    # escala del arma en tercera persona (los jugadores de Minecraft son robustos)
    "scale": 0.8,
    # desplazamiento extra de la empunadura respecto al punto de agarre (px, espacio del cuerpo)
    "hand_offset_px": (0.0, 0.0, 0.0),
}
