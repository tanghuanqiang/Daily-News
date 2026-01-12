/// <reference types="vite/client" />

export {}

declare module '*.module.css' {
  const classes: { [key: string]: string }
  export default classes
}
