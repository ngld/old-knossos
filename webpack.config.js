const path = require('path');
const webpack = require('webpack');
const VueLoaderPlugin = require('vue-loader/lib/plugin');

const use_webkit = process.env.USE_WEBKIT === 'True';

const config = {
  entry: './html/js/main.js',
  plugins: [
    new VueLoaderPlugin()
  ],
  module: {
    rules: [
      {
        test: /\.js$/,
        exclude: file => (
          /node_modules/.test(file) &&
          !/\.vue\.js/.test(file)
        ),
        loader: 'buble-loader',
        options: {
          objectAssign: 'Object.assign',
          transforms: (use_webkit ? {
            arrow: true,
            classes: true,
            conciseMethodProperty: true,
            templateString: true,
            destructuring: true,
            parameterDestructuring: true,
            defaultParameter: true,
            letConst: true,
            computedProperty: true,

            dangerousForOf: true,
            modules: false
          } : {
            dangerousForOf: true,
            modules: false
          })
        }
      },
      {
        test: /\.vue$/,
        loader: 'vue-loader',
        options: {
          preserveWhitespace: false
        }
      },
      {
        test: /\.css$/,
        use: ['vue-style-loader', 'css-loader']
      },
      {
        test: /\.(png|svg|gif|ttf|woff2?)$/,
        use: ['file-loader']
      }
    ]
  }
};

module.exports = [
  Object.assign({}, config, {
    mode: 'production',
    output: {
      filename: 'bundle.js',
      path: path.resolve(__dirname, 'html/dist'),
      publicPath: 'dist/'
    },
    plugins: config.plugins.concat([
      new webpack.DefinePlugin({
        'process.env.NODE_ENV': '"production"',
        USE_WEBKIT: JSON.stringify(use_webkit),
        KN_DEBUG: JSON.stringify(false)
      })
    ])
  }),

  Object.assign({}, config, {
    mode: 'development',
    output: {
      filename: 'debug_bundle.js',
      path: path.resolve(__dirname, 'html/dist'),
      publicPath: 'dist/'
    },
    plugins: config.plugins.concat([
      new webpack.DefinePlugin({
        'process.env.NODE_ENV': '"dev"',
        USE_WEBKIT: JSON.stringify(use_webkit),
        KN_DEBUG: JSON.stringify(true)
      })
    ])
  })
];
