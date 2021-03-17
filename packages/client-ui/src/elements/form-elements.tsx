import {action} from 'mobx';
import {observer} from 'mobx-react-lite';
import {Checkbox, ICheckboxProps, InputGroup, IInputGroupProps2} from '@blueprintjs/core';
import {useFormContext} from './form-context';

interface FormCheckboxProps extends ICheckboxProps {
  name: string;
}
export const FormCheckbox = observer(function FormCheckbox(props: FormCheckboxProps): React.ReactElement {
  const ctx = useFormContext();
  const name = props.name;

  return <Checkbox checked={!!ctx[name]} onChange={action((e) => {
    console.log(e.target);
    ctx[name] = (e.target as HTMLInputElement).checked;
  })} {...props} />;
});

interface FormInputGroupProps extends IInputGroupProps2 {
  name: string;
}
export const FormInputGroup = observer(function FormInputGroup(props: FormInputGroupProps): React.ReactElement {
  const ctx = useFormContext();
  const name = props.name;

  return <InputGroup value={ctx[name] as string} onChange={action((e) => {
    ctx[name] = e.target.value;
  })} {...props} />;
});
