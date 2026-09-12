declare module 'alpinejs' {
  const Alpine: {
    data: (name: string, factory: () => Record<string, unknown>) => void;
    start: () => void;
  };
  export default Alpine;
}
