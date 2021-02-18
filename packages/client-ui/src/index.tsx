import React from 'react';
import ReactDOM from 'react-dom';
import './style.css';
import { FocusStyleManager, H1 } from '@blueprintjs/core';
import { BrowserRouter } from 'react-router-dom';

import Start from './pages/start';
import { GlobalState, StateProvider } from './lib/state';

FocusStyleManager.onlyShowFocusOnTabs();

ReactDOM.render(
  <StateProvider value={new GlobalState({})}>
    <BrowserRouter>
      <Start />
    </BrowserRouter>
  </StateProvider>,
  document.querySelector('#container'),
);

