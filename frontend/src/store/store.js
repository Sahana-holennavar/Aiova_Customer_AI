import { configureStore } from "@reduxjs/toolkit";
import complaintsReducer from "./slices/complaintsSlice";

export const store = configureStore({
  reducer: {
    complaints: complaintsReducer,
  },
});
