// src/components/Avatar2.jsx
import React, { useRef, useEffect, useState } from "react";
import { useGLTF, useAnimations } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { button, useControls } from "leva";
import * as THREE from "three";
import { useChat } from "../hooks/useChat";

const facialExpressions = {
  default: {},
  smile: {
    mouthSmileLeft: 1,
    mouthSmileRight: 1,
    cheekSquintLeft: 0.4,
    cheekSquintRight: 0.4,
    browInnerUp: 0.2,
  },
  sad: {
    mouthFrownLeft: 1,
    mouthFrownRight: 1,
    mouthShrugLower: 0.8,
    browInnerUp: 0.5,
    eyeSquintLeft: 0.7,
    eyeSquintRight: 0.7,
  },
  angry: {
    browDownLeft: 1,
    browDownRight: 1,
    eyeSquintLeft: 1,
    eyeSquintRight: 1,
    mouthFunnel: 0.6,
    noseSneerLeft: 1,
    noseSneerRight: 0.5,
  },
  surprised: {
    eyeWideLeft: 0.8,
    eyeWideRight: 0.8,
    jawOpen: 1,
    mouthFunnel: 0.7,
    browInnerUp: 1,
  },
};

const visemeMap = {
  A: "viseme_PP",
  B: "viseme_kk",
  C: "viseme_I",
  D: "viseme_aa",
  E: "viseme_O",
  F: "viseme_U",
  G: "viseme_FF",
  H: "viseme_TH",
  X: "viseme_PP",
};

let setupMode = false;

export function Avatar2(props) {
  const group = useRef();
  const { nodes, materials, animations, scene } = useGLTF("/models/dora_iter_final.glb");

  const { message, onMessagePlayed, chat } = useChat();
  const [lipsync, setLipsync] = useState();
  const [facialExpression, setFacialExpression] = useState("");
  const [blink, setBlink] = useState(false);
  const [winkLeft, setWinkLeft] = useState(false);
  const [winkRight, setWinkRight] = useState(false);
  const [audio, setAudio] = useState();

  const { actions, mixer } = useAnimations(animations, group);

  // Ensure Idle always runs
  // Ensure the first animation always runs as Idle
useEffect(() => {
  if (animations.length === 0) return;

  const idleAction = actions[animations[0].name];
  if (idleAction) {
    idleAction.reset().fadeIn(0.3).play();
    idleAction.setLoop(THREE.LoopRepeat, Infinity);
  }
}, [actions, animations]);


  // Handle chat messages and facial/lipsync
  useEffect(() => {
    if (!message) return;

    setFacialExpression(message.facialExpression || "");
    setLipsync(message.lipsync);

    const audioEl = new Audio("data:audio/mp3;base64," + message.audio);
    audioEl.play();
    setAudio(audioEl);
    audioEl.onended = () => {
      onMessagePlayed();
    };
  }, [message, onMessagePlayed]);

  const lerpMorphTarget = (target, value, speed = 0.1) => {
    scene.traverse((child) => {
      if (child.isSkinnedMesh && child.morphTargetDictionary) {
        const index = child.morphTargetDictionary[target];
        if (index !== undefined) {
          child.morphTargetInfluences[index] = THREE.MathUtils.lerp(
            child.morphTargetInfluences[index],
            value,
            speed
          );
        }
      }
    });
  };

  useFrame(() => {
    // Apply facial expressions
    !setupMode &&
      Object.keys(facialExpressions[facialExpression] || {}).forEach((key) => {
        lerpMorphTarget(key, facialExpressions[facialExpression][key], 0.1);
      });

    // Blink/Wink
    lerpMorphTarget("eyeBlinkLeft", blink || winkLeft ? 1 : 0, 0.3);
    lerpMorphTarget("eyeBlinkRight", blink || winkRight ? 1 : 0, 0.3);

    // Lipsync while keeping Idle animation running
    if (setupMode || !message || !lipsync || !audio) return;

    const currentTime = audio.currentTime;
    const activeMorphs = [];

    lipsync.mouthCues.forEach((cue) => {
      if (currentTime >= cue.start && currentTime <= cue.end) {
        const target = visemeMap[cue.value];
        if (target) {
          lerpMorphTarget(target, 1, 0.2);
          activeMorphs.push(target);
        }
      }
    });

    Object.values(visemeMap).forEach((v) => {
      if (!activeMorphs.includes(v)) lerpMorphTarget(v, 0, 0.1);
    });
  });

  // Automatic blink
  useEffect(() => {
    let blinkTimeout;
    const nextBlink = () => {
      blinkTimeout = setTimeout(() => {
        setBlink(true);
        setTimeout(() => {
          setBlink(false);
          nextBlink();
        }, 200);
      }, THREE.MathUtils.randInt(1000, 4000));
    };
    nextBlink();
    return () => clearTimeout(blinkTimeout);
  }, []);

  // Leva controls
  useControls("Avatar Controls", {
    chat: button(() => chat()),
    winkLeft: button(() => {
      setWinkLeft(true);
      setTimeout(() => setWinkLeft(false), 300);
    }),
    winkRight: button(() => {
      setWinkRight(true);
      setTimeout(() => setWinkRight(false), 300);
    }),
    facialExpression: {
      options: Object.keys(facialExpressions),
      onChange: (val) => setFacialExpression(val),
    },
    enableSetupMode: button(() => (setupMode = true)),
    disableSetupMode: button(() => (setupMode = false)),
  });

  return (
    <group ref={group} {...props} dispose={null}>
      <group name="Scene">
        <group name="Armature" rotation={[Math.PI / 2, 0, 0]} scale={0.01}>
          <skinnedMesh
            name="avaturn_hair_0"
            geometry={nodes.avaturn_hair_0.geometry}
            material={materials['avaturn_hair_0_material.003']}
            skeleton={nodes.avaturn_hair_0.skeleton}
          />
          <skinnedMesh
            name="avaturn_hair_1"
            geometry={nodes.avaturn_hair_1.geometry}
            material={materials['avaturn_hair_1_material.003']}
            skeleton={nodes.avaturn_hair_1.skeleton}
          />
          <skinnedMesh
            name="avaturn_look_0"
            geometry={nodes.avaturn_look_0.geometry}
            material={materials['avaturn_look_0_material.003']}
            skeleton={nodes.avaturn_look_0.skeleton}
          />
          <skinnedMesh
            name="avaturn_shoes_0"
            geometry={nodes.avaturn_shoes_0.geometry}
            material={materials['avaturn_shoes_0_material.003']}
            skeleton={nodes.avaturn_shoes_0.skeleton}
          />
          <skinnedMesh
            name="Body_Mesh"
            geometry={nodes.Body_Mesh.geometry}
            material={materials['Body.003']}
            skeleton={nodes.Body_Mesh.skeleton}
          />
          <skinnedMesh
            name="Eye_Mesh"
            geometry={nodes.Eye_Mesh.geometry}
            material={materials['Eyes.003']}
            skeleton={nodes.Eye_Mesh.skeleton}
            morphTargetDictionary={nodes.Eye_Mesh.morphTargetDictionary}
            morphTargetInfluences={nodes.Eye_Mesh.morphTargetInfluences}
          />
          <skinnedMesh
            name="EyeAO_Mesh"
            geometry={nodes.EyeAO_Mesh.geometry}
            material={materials.Body}
            skeleton={nodes.EyeAO_Mesh.skeleton}
            morphTargetDictionary={nodes.EyeAO_Mesh.morphTargetDictionary}
            morphTargetInfluences={nodes.EyeAO_Mesh.morphTargetInfluences}
          />
          <skinnedMesh
            name="Eyelash_Mesh"
            geometry={nodes.Eyelash_Mesh.geometry}
            material={materials['Eyelash.003']}
            skeleton={nodes.Eyelash_Mesh.skeleton}
            morphTargetDictionary={nodes.Eyelash_Mesh.morphTargetDictionary}
            morphTargetInfluences={nodes.Eyelash_Mesh.morphTargetInfluences}
          />
          <skinnedMesh
            name="Head_Mesh"
            geometry={nodes.Head_Mesh.geometry}
            material={materials['Head.003']}
            skeleton={nodes.Head_Mesh.skeleton}
            morphTargetDictionary={nodes.Head_Mesh.morphTargetDictionary}
            morphTargetInfluences={nodes.Head_Mesh.morphTargetInfluences}
          />
          <skinnedMesh
            name="Teeth_Mesh"
            geometry={nodes.Teeth_Mesh.geometry}
            material={materials['Teeth.005']}
            skeleton={nodes.Teeth_Mesh.skeleton}
            morphTargetDictionary={nodes.Teeth_Mesh.morphTargetDictionary}
            morphTargetInfluences={nodes.Teeth_Mesh.morphTargetInfluences}
          />
          <skinnedMesh
            name="Tongue_Mesh"
            geometry={nodes.Tongue_Mesh.geometry}
            material={materials['Teeth.006']}
            skeleton={nodes.Tongue_Mesh.skeleton}
            morphTargetDictionary={nodes.Tongue_Mesh.morphTargetDictionary}
            morphTargetInfluences={nodes.Tongue_Mesh.morphTargetInfluences}
          />
          <primitive object={nodes.mixamorigHips} />
        </group>
        <group name="Armature001" position={[1.232, 0, 0]}>
          <primitive object={nodes.Hips} />
        </group>
        <group name="Armature002" position={[1.143, 0, 0]}>
          <primitive object={nodes.Hips_1} />
        </group>
        <group name="Armature003" position={[1.191, 0, 0]}>
          <primitive object={nodes.Hips_2} />
        </group>
      </group>
    </group>
  );
}

useGLTF.preload("/models/dora_iter_final.glb");
