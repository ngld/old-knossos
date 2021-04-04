import React from 'react';
import ReactDOM from 'react-dom';
import './tw-index.css';
import './blueprint.scss';
import '@blueprintjs/popover2/lib/css/blueprint-popover2.css';
import './resources/fonts/index.css';
import './style.css';
import { FocusStyleManager, H1 } from '@blueprintjs/core';
import { BrowserRouter } from 'react-router-dom';
import { DefaultContext as IconConfig } from '@meronex/icons';

import Root from './elements/root';
import { GlobalState, StateProvider } from './lib/state';

FocusStyleManager.onlyShowFocusOnTabs();
IconConfig.className = 'icon';

ReactDOM.render(
  <StateProvider value={new GlobalState()}>
    <BrowserRouter>
      <Root />
    </BrowserRouter>
  </StateProvider>,
  document.querySelector('#container'),
);

