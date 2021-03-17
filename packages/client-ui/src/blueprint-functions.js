/*
 * Copyright 2019 Palantir Technologies, Inc. All rights reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

const types = require('node-sass').types;
const svgToDataUri = require('mini-svg-data-uri');
const icons = require('@blueprintjs/icons');

module.exports = {
  /**
   * Sass function to inline a UI icon svg and change its path color.
   *
   * Usage:
   * svg-icon("16px/icon-name.svg", (path: (fill: $color)) )
   */
  'svg-icon': (path, selector) => {
    // Unfortunately we can't use the same code @blueprintjs/core uses for their function since we don't have the
    // raw svg files. Instead we build minimal svgs from the info provided in @blueprintjs/icons.
    path = path.getValue();
    const collection = path.substring(0, 5) === '16px/' ? icons.IconSvgPaths16 : icons.IconSvgPaths20;
    const name = path.substring(5, path.indexOf('.'));

    let content = '<?xml version="1.0" encoding="utf-8"?>\n<svg version="1.1" xmlns="http://www.w3.org/2000/svg" ';
    if (path.substring(0, 5) === '16px/') {
      content += 'viewBox="0 0 16 16"';
    } else {
      content += 'viewBox="0 0 20 20"';
    }
    content += '>\n<g><path fill="' + selector.getValue(0).getValue(0) + '" d="' + collection[name] + '"/></g></svg>';
    return new types.String('url("' + svgToDataUri(content.toString('UTF-8')) + '")');
  }
};
