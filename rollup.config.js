import minifyHTML from '@lit-labs/rollup-plugin-minify-html-literals';
import { nodeResolve } from '@rollup/plugin-node-resolve';
import terser from '@rollup/plugin-terser';

export default [
  {
    input: 'www/dresden-transport-card.js',
    output: {
      dir: 'dist',
      format: 'iife',
      sourcemap: true,
    },
    plugins: [
      nodeResolve(),
      minifyHTML(),
      terser({
        module: true
      }),
    ],
  },
];
