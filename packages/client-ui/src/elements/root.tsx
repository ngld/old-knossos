import {
  CiWindowMinLine,
  CiWindowRestoreLine,
  CiWindowCloseLine,
  CiPictureLine,
  CiFilterLine,
  CiCogLine,
} from '@meronex/icons/ci';
import { observer } from 'mobx-react-lite';
import { Tooltip2 } from '@blueprintjs/popover2';
import cx from 'classnames';
import HoverLink from './hover-link';
import { useGlobalState } from '../lib/state';
import TaskDisplay from './task-display';
import LocalModList from '../pages/local-mod-list';
import Settings from '../pages/settings';

const NavTabs = observer(function NavTabs(): React.ReactElement {
  const gs = useGlobalState();
  const items = {
    play: 'Play',
    explore: 'Explore',
    build: 'Build',
  };

  return (
    <div className="ml-32 mt-2">
      {Object.entries(items).map(([key, label]) => (
        <a
          key={key}
          href="#"
          className={
            'text-white ml-10 pb-1 border-b-4' + (gs.activeTab === key ? '' : ' border-transparent')
          }
          onClick={(e) => {
            e.preventDefault();
            gs.switchTo(key);
          }}
        >
          {label}
        </a>
      ))}
    </div>
  );
});

interface TooltipButtonProps {
  tooltip?: string;
  onClick?: () => void;
  children: React.ReactNode | React.ReactNode[];
}
function TooltipButton(props: TooltipButtonProps): React.ReactElement {
  return (
    <Tooltip2 content={props.tooltip} placement="bottom">
      <a
        href="#"
        onClick={(e) => {
          e.preventDefault();
          if (props.onClick) props.onClick();
        }}
      >
        {props.children}
      </a>
    </Tooltip2>
  );
}

const ModContainer = observer(function ModContainer(): React.ReactElement {
  const gs = useGlobalState();

  return (
    <div
      className={cx(
        'flex-1',
        'mod-container',
        { 'pattern-bg': gs.activeTab !== 'settings' },
        'rounded-md',
        'm-3',
        'p-4',
      )}
    >
      {gs.activeTab === 'play' ? (
        <LocalModList />
      ) : gs.activeTab === 'settings' ? (
        <Settings />
      ) : (
        <div>Page not found</div>
      )}
    </div>
  );
});

export default function Root(): React.ReactElement {
  const gs = useGlobalState();

  return (
    <div className="flex flex-col h-full">
      <div className="flex-initial">
        <div className="mt-5 ml-5 text-3xl text-white font-inria">
          <span>Knossos</span>
          <span className="ml-10">1.0.0</span>
          <span className="ml-1 text-sm align-top">+c3fa30</span>
        </div>

        <div className="absolute top-0 right-0 text-white text-3xl">
          <HoverLink>
            <CiWindowMinLine />
          </HoverLink>
          <HoverLink>
            <CiWindowRestoreLine />
          </HoverLink>
          <HoverLink>
            <CiWindowCloseLine />
          </HoverLink>
        </div>

        <div className="mt-3 relative">
          <div className="bg-dim h-px" />
          <TaskDisplay />
        </div>

        <div className="float-right mr-2 text-white text-2xl gap-2">
          <TooltipButton tooltip="Screenshots">
            <CiPictureLine className="ml-2" />
          </TooltipButton>
          <CiFilterLine className="ml-2" />
          <TooltipButton tooltip="Settings" onClick={() => gs.switchTo('settings')}>
            <CiCogLine className="ml-2" />
          </TooltipButton>
        </div>

        <NavTabs />
      </div>
      <ModContainer />
    </div>
  );
}
