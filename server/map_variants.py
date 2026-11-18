"""Independently cooked map roots sharing one installed feature bundle."""
SIMULATION_NAMES=('Anomaly','Charlie','Divide','Faceoff','Hectic','Moshpit')
MAP_VARIANTS={f'MAP_Simulation_{name}':('MAP_Simulation',f'/MAP_Simulation/Simulation{name}/Simulation{name}_Main') for name in SIMULATION_NAMES}


def expanded_features(features):
    result=set(features)
    for mid,(feature,root) in MAP_VARIANTS.items():
        if feature in features:result.add(mid)
    return sorted(result-{'MAP_Simulation'})


def feature_root(mid):
    return MAP_VARIANTS.get(mid,(mid,None))
