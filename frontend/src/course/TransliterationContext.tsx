import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

import { getProfile, patchProfile } from "../courseApi";

interface TransliterationValue {
  show: boolean;
  setShow: (value: boolean) => void;
}

export const TransliterationContext = createContext<TransliterationValue>({
  show: true,
  setShow: () => {},
});

export function useTransliteration(): TransliterationValue {
  return useContext(TransliterationContext);
}

export function TransliterationProvider({ children }: { children: ReactNode }) {
  const [show, setShowState] = useState(true);

  useEffect(() => {
    getProfile()
      .then((profile) => setShowState(profile.show_transliteration))
      .catch(() => setShowState(true));
  }, []);

  const setShow = (value: boolean) => {
    setShowState(value);
    patchProfile({ show_transliteration: value }).catch(() => {});
  };

  return (
    <TransliterationContext.Provider value={{ show, setShow }}>
      {children}
    </TransliterationContext.Provider>
  );
}
