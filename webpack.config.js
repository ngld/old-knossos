const path = require('path');
const webpack = require('webpack');

const use_webkit = process.env.USE_WEBKIT === 'True';

const config = {
  entry: './html/js/main.js',
  plugins: [
    new webpack.LoaderOptionsPlugin({
      options: {
        buble: {
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
      }
    })
  ],
  module: {
    rules: [
      {
        test: /\.js$/,
        use: ['buble-loader']
      },
      {
        test: /\.vue$/,
        use: ['vue-loader']
      },
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader']
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
      }),
      new webpack.optimize.UglifyJsPlugin({
        ecma: 5
      })
    ])
  }),

  Object.assign({}, config, {
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
