import { BrowserRouter, Route, Routes } from 'react-router';

function HomePlaceholder() {
  return <h1>마감 직전</h1>;
}

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePlaceholder />} />
      </Routes>
    </BrowserRouter>
  );
}
