import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import '@/app/styles/tokens.css';
import '@/app/styles/bundle.css';
import { App } from '@/app/App';
import { createContainer } from '@/app/container';
import { DepsProvider } from '@/shared/lib/DepsProvider';

const container = createContainer();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <DepsProvider container={container}>
      <App />
    </DepsProvider>
  </StrictMode>,
);
