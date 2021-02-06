const path = require('path');
const webpack = require('webpack');
const { merge } = require('webpack-merge');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const DuplicatePackageCheckerPlugin = require('duplicate-package-checker-webpack-plugin');

// dev
const ReactRefreshPlugin = require('@pmmmwh/react-refresh-webpack-plugin');

// prod
const zopfli = require('@gfx/zopfli');
const zlib = require('zlib');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const CompressionPlugin = require('compression-webpack-plugin');

module.exports = function (env, args) {
  const production = env.production;

  const baseConfig = {
    mode: production ? 'production' : 'development',
    devtool: production ? 'source-map' : 'eval',
    entry: './src/index.tsx',
    output: {
      path: path.resolve(__dirname, 'dist'),
      filename: production
        ? 'js/[name].[contenthash:7].js'
        : 'js/[name].js',
      chunkFilename: production
        ? 'js/[name].[contenthash:7].js'
        : 'js/[name].js',
      publicPath: '/',
    },
    optimization: {
      splitChunks: {
        chunks: 'all',
      },
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
        '@api': path.resolve(__dirname, '../api/api'),
      },
      extensions: [
        '.tsx',
        '.ts',
        '.jsx',
        '.js',
      ],
    },
    module: {
      rules: [
        {
          test: /\.css$/,
          use: [
            (production ? MiniCssExtractPlugin.loader : 'style-loader'),
            'css-loader',
            'postcss-loader',
          ],
        },
        {
          test: /\.(png|jpe?g|gif)$/,
          loader: 'file-loader',
          options: {
            name: 'img/[name].[ext]',
          },
        },
        {
          test: /\.(ttf|eot|otf|woff2?)$/,
          loader: 'file-loader',
          options: {
            name: 'fonts/[name].[ext]',
          },
        },
      ],
    },
  };

  const babelRule = (flavor) => ({
    output: {
      path: path.resolve(__dirname, 'dist', flavor),
    },
    module: {
      rules: [
        {
          test: /\.[tj]sx?$/,
          include: [
            path.resolve(__dirname, './src'),
            path.resolve(__dirname, '../api/api'),
          ],
          use: [
            {
              loader: 'babel-loader',
              options: {
                configFile: path.resolve(
                  __dirname,
                  `babel-${flavor}.config.js`,
                ),
              },
            },
          ],
        },
      ],
    },
  });

  const devConfig = {
    plugins: [
      new webpack.DefinePlugin({
        __DEV__: 'true',
        'process.env.NODE_ENV': '"development"',
        'process.env.BLUEPRINT_NAMESPACE': 'null',
        'process.env.REACT_APP_BLUEPRINT_NAMESPACE': 'null',
        'global': 'window',
      }),
      new MiniCssExtractPlugin({
        filename: 'css/[name].css',
        chunkFilename: 'css/[id].css',
      }),
      new HtmlWebpackPlugin({
        template: path.resolve(__dirname, './html.ejs'),
      }),
      new ReactRefreshPlugin(),
    ],
    devServer: {
      publicPath: '/',
      hot: true,
      historyApiFallback: {
        rewrites: [
          { from: /./, to: '/index.html' },
        ],
      },
      proxy: {
        '/twirp': 'http://localhost:8200/',
      },
    },
  };

  const prodConfig = {
    plugins: [
      new webpack.DefinePlugin({
        __DEV__: 'false',
        'process.env.NODE_ENV': '"production"',
        'process.env.BLUEPRINT_NAMESPACE': 'null',
        'process.env.REACT_APP_BLUEPRINT_NAMESPACE': 'null',
        'global': 'window',
      }),
      new CleanWebpackPlugin(),
      new MiniCssExtractPlugin({
        filename: 'css/[name].[contenthash].css',
        chunkFilename: 'css/[id].[contenthash].css',
      }),
      // zopfli / .gz compression
      new CompressionPlugin({
        test: /\.(js|css|html)$/,
        compressionOptions: {
          numiterations: 15,
        },
        algorithm(input, compressionOptions, callback) {
          return zopfli.gzip(input, compressionOptions, callback);
        },
        threshold: 10240,
        minRatio: 0.8,
        deleteOriginalAssets: false,
      }),
      // brotli / .br compression
      new CompressionPlugin({
        filename: '[path][base].br',
        algorithm: 'brotliCompress',
        test: /\.(js|css|html)$/,
        compressionOptions: {
          params: {
            [zlib.constants.BROTLI_PARAM_QUALITY]: 11,
          },
        },
        threshold: 10240,
        minRatio: 0.8,
        deleteOriginalAssets: false,
      }),
      new HtmlWebpackPlugin({
        template: path.resolve(__dirname, './html.ejs'),
      }),
      new DuplicatePackageCheckerPlugin(),
    ],
  };

  return env.production
    ? merge(baseConfig, prodConfig, babelRule('prod'))
    : merge(baseConfig, devConfig, babelRule('dev'));
};
