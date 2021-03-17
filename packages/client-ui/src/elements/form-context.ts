import {createContext, useContext} from 'react';

const ctx = createContext<Record<string, unknown>>({});
export default ctx.Provider;

export function useFormContext(): Record<string, unknown> {
  return useContext(ctx);
}
