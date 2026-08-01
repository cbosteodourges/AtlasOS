# ATLAS OS — Anatomical Model Attribution

## Anatomical assets

The anatomical 3D assets contained in this directory are derived from the Z-Anatomy project and include anatomical data originating from BodyParts3D.

### Z-Anatomy

- Project: Z-Anatomy — The libre 3D atlas of anatomy
- Source: https://github.com/Z-Anatomy/The-blend
- Website: https://www.z-anatomy.com/
- License: Creative Commons Attribution-ShareAlike 4.0 International
- License URL: https://creativecommons.org/licenses/by-sa/4.0/

Required attribution:

> Z-Anatomy — The libre 3D atlas of anatomy — CC BY-SA 4.0.

### BodyParts3D

- Project: BodyParts3D
- Creator: The Database Center for Life Science
- Source: https://lifesciencedb.jp/bp3d/
- License applicable to the source models used by Z-Anatomy: Creative Commons Attribution-ShareAlike 2.1 Japan
- License URL: https://creativecommons.org/licenses/by-sa/2.1/jp/deed.en

Required attribution:

> BodyParts3D, © The Database Center for Life Science, licensed under CC Attribution-ShareAlike 2.1 Japan.

## Modifications made for ATLAS OS

The source anatomical model was processed for integration into the ATLAS OS interactive biomechanical digital twin.

Modifications performed on 1 August 2026 include:

- conversion from Blender format to glTF Binary (`.glb`);
- extraction of the lower-limb anatomical structures;
- separation into skeleton, joint, muscle/tendon and insertion layers;
- temporary flattening of the Blender hierarchy while preserving world transforms;
- exclusion of technical guide objects without visible surfaces;
- preservation of original anatomical object names;
- preservation of individual selectable anatomical objects;
- preservation of source geometry and materials;
- no mesh decimation;
- no destructive geometry merging;
- no Draco compression.

The original `Startup.blend` source file was not modified.

## Exported anatomical layers

- `atlas_membre_inferieur_squelette.glb`
- `atlas_membre_inferieur_articulations.glb`
- `atlas_membre_inferieur_muscles_tendons.glb`
- `atlas_membre_inferieur_insertions.glb`

## ATLAS OS notice

These anatomical assets and any adaptations of them must remain attributed to their original creators and distributed in accordance with the applicable Creative Commons Attribution-ShareAlike licenses.

ATLAS OS software components developed independently around these assets retain their own applicable licensing terms.

These models are intended for educational, biomechanical visualisation and decision-support purposes. They do not constitute a medical diagnosis.