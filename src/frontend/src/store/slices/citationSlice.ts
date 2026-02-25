import { createSlice, PayloadAction } from '@reduxjs/toolkit';

/**
 * Represents a citation source
 */
export interface Citation {
    id: string;
    title: string;
    content: string;
    source: string;
    url?: string;
    pageNumber?: number;
    relevanceScore?: number;
}

/**
 * Citation slice - handles citation/reference state
 */
export interface CitationState {
    /** List of citations for current context */
    citations: Citation[];
    /** Currently selected/active citation */
    activeCitation: Citation | null;
    /** Whether citation panel is open */
    isPanelOpen: boolean;
    /** Whether citations are loading */
    isLoading: boolean;
}

const initialState: CitationState = {
    citations: [],
    activeCitation: null,
    isPanelOpen: false,
    isLoading: false,
};

const citationSlice = createSlice({
    name: 'citation',
    initialState,
    reducers: {
        setCitations: (state, action: PayloadAction<Citation[]>) => {
            state.citations = action.payload;
        },
        addCitation: (state, action: PayloadAction<Citation>) => {
            state.citations.push(action.payload);
        },
        removeCitation: (state, action: PayloadAction<string>) => {
            state.citations = state.citations.filter(c => c.id !== action.payload);
        },
        setActiveCitation: (state, action: PayloadAction<Citation | null>) => {
            state.activeCitation = action.payload;
        },
        openCitationPanel: (state) => {
            state.isPanelOpen = true;
        },
        closeCitationPanel: (state) => {
            state.isPanelOpen = false;
            state.activeCitation = null;
        },
        toggleCitationPanel: (state) => {
            state.isPanelOpen = !state.isPanelOpen;
            if (!state.isPanelOpen) {
                state.activeCitation = null;
            }
        },
        setIsLoading: (state, action: PayloadAction<boolean>) => {
            state.isLoading = action.payload;
        },
        /**
         * Reset citation state to initial values
         */
        resetCitationState: () => initialState,
        /**
         * Select a citation and open the panel
         */
        selectCitation: (state, action: PayloadAction<Citation>) => {
            state.activeCitation = action.payload;
            state.isPanelOpen = true;
        },
    },
});

export const {
    setCitations,
    addCitation,
    removeCitation,
    setActiveCitation,
    openCitationPanel,
    closeCitationPanel,
    toggleCitationPanel,
    setIsLoading,
    resetCitationState,
    selectCitation,
} = citationSlice.actions;

export default citationSlice.reducer;
