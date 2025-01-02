module.exports = {
  env: {
    test: {
      presets: ['@babel/preset-env'],
      plugins: ['@babel/plugin-transform-class-properties', '@babel/plugin-transform-private-methods']
    }
  }
};