/**
 * Typed Redux Hooks
 *
 * Pre-typed versions of useDispatch and useSelector so every component
 * automatically gets correct RootState / AppDispatch types.
 */
import { useDispatch, useSelector, type TypedUseSelectorHook } from 'react-redux';
import type { RootState, AppDispatch } from './store';

/** Use throughout the app instead of plain `useDispatch` */
export const useAppDispatch: () => AppDispatch = useDispatch;

/** Use throughout the app instead of plain `useSelector` */
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;
