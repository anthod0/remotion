import {AbsoluteFill, Composition, registerRoot} from 'remotion';

const ColorBars = () => (
  <AbsoluteFill style={{flexDirection: 'row'}}>
    {['#ff0000', '#008000', '#0000ff', '#808080'].map((color) => (
      <div key={color} style={{flex: 1, backgroundColor: color}} />
    ))}
  </AbsoluteFill>
);

registerRoot(() => (
  <Composition
    id="ColorBars"
    component={ColorBars}
    width={640}
    height={360}
    fps={30}
    durationInFrames={30}
  />
));
