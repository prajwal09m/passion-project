// Ambient type declaration for animejs v3.2.x. The package ships no .d.ts
// and the maintained @types/animejs targets v2 API; declaring the real
// v3.2.x surface here keeps us type-safe.
declare module "animejs" {
  export type AnimateParams = Record<string, unknown> & {
    duration?: number;
    delay?: number | number[] | ((el: unknown, i: number, total: number) => number);
    ease?: string | ((t: number) => number);
    loop?: number | boolean;
    alternate?: boolean;
    autoplay?: boolean;
  };

  export type StaggerParams = {
    from?: "first" | "last" | "center" | number;
    direction?: "normal" | "reverse";
    ease?: string | ((t: number) => number);
    grid?: [number, number];
    axis?: "x" | "y";
    start?: number;
  };

  export type TimelineParams = {
    defaults?: AnimateParams;
    autoplay?: boolean;
    loop?: number | boolean;
  };

  export interface Animation {
    play(): Animation;
    pause(): Animation;
    restart(): Animation;
    reverse(): Animation;
    cancel(): Animation;
    add(target: unknown, params: AnimateParams): Animation;
    set(target: unknown, params: AnimateParams): Animation;
    then(cb: () => void): Animation;
  }

  // Permissive target: real animejs v3 accepts selectors, single elements,
  // NodeList, arrays, and arbitrary objects.
  export type AnimateTarget =
    | string
    | Element
    | NodeList
    | ArrayLike<unknown>
    | object
    | null;

  export function animate(target: AnimateTarget, params: AnimateParams): Animation;
  export function stagger(
    value: number | string,
    params?: StaggerParams
  ): (el: unknown, i: number, total: number) => number;
  export function timeline(params?: TimelineParams): Animation;

  const _default: typeof animate;
  export default _default;
}
