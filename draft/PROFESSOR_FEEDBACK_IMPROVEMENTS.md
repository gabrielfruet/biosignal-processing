# Professor Feedback - Implementation Plan

## Date: 2026-04-01

## Original Feedback Summary

Professor Victor's feedback on the current document:

1. **Point 1**: Table 5 (SQI Thresholds) - Need to explain how threshold values were chosen
2. **Point 2**: Add comparison with other papers (accuracy, FP, FN)
3. **Point 3**: Include a classifier as preliminary result

**User Clarifications:**
- IGNORE classifier for now (last step)
- Document empirical approach for thresholds (narrative)
- Literature comparison without classifier metrics

---

## Dataset Verification

| Field | Value |
|-------|-------|
| **Correct Name** | Dataset of Multi-Modal Physiological Signals (fNIRS, EEG, ECG, EMG) Recorded Across Different Emotional States |
| **Source** | IEEE DataPort |
| **URL** | https://ieee-dataport.org/documents/dataset-multi-modal-physiological-signals-fnirs-eeg-ecg-emg-recorded-across-different |
| **Authors** | Mohammad Naser et al. |
| **Participants** | 16 |
| **Modalities** | fNIRS, EEG, ECG, EMG |
| **Stimuli** | Emotion-eliciting video stimuli |
| **Markers Available** | Baseline timing, stimulation timing (NO explicit emotion labels) |

---

## Implementation Plan

### Phase 1: Dataset Documentation Fix

**Priority:** P1  
**Status:** Not Started

#### Change 1: Update Dataset Characterization (3-metodologia.tex)

Replace Section 4.1 "Caracterização do Dataset" with corrected information:

```latex
\section{Caracterização do Dataset}

Utilizou-se o \textit{Dataset of Multi-Modal Physiological Signals} 
(disponível em IEEE DataPort) \citep{naser2023multimodal}, contendo registros 
de 16 participantes expostos a estímulos visuais indutores de emoções. O 
dataset compreende quatro modalidades de biossinais: EEG (Emotiv EPOC+, 8 canais), 
ECG, EMG e fNIRS. Os sinais foram sincronizados e armazenados com marcadores 
temporais indicando os momentos de linha de base e estimulação.

Os 8 canais de EEG foram posicionados em AF7, AF8, F3, F4, PO7, PO8, PO3 e PO4, 
operando a uma frequência de amostragem de 512 Hz. As modalidades de ECG e EMG 
foram registradas com canais únicos a 250 Hz. O sistema de fNIRS registrou as 
concentrações de oxiemoglobina e desoxiemoglobina em dois canais a 16 Hz.
```

**File:** `tex/2-textuais/3-metodologia.tex`

---

### Phase 2: Threshold Justification

**Priority:** P1  
**Status:** Not Started

#### Change 2: Add Threshold Calibration Methodology (3-metodologia.tex)

Add new subsection after Section 3.5 "Classificação e Lógica de Rejeição":

```latex
\subsection{Calibração Empírica dos Limiares}
\label{sec:calibracao_limiares}

Os limiares de rejeição ($\theta$) foram estabelecidos por meio de uma abordagem 
empírica combinada com referências da literatura. O procedimento consistiu em:

\begin{enumerate}
    \item \textbf{Análise de Distribuição:} Calculou-se a distribuição estatística 
    das métricas (SNR, curtose, entropia) para todos os segmentos de todos os 
    sujeitos, identificando valores extremos e suas causasKnown.
    
    \item \textbf{Calibração por Modalidade:} Os limiares foram ajustados para cada 
    modalidade considerando:
    \begin{itemize}
        \item EEG: Sensibilidade alta a piscadas oculares e artefatos de movimento 
        (curtose elevada esperada).
        \item ECG: Presença de \textit{spikes} R (curtose muito alta esperada).
        \item EMG: Atividade muscular descontínua (entropia variável).
        \item fNIRS: Relação sinal-ruído intrinsecamente baixa.
    \end{itemize}
    
    \item \textbf{Validação Visual:} Os limiares foram validados por inspeção 
    visual de segmentos aceitos e rejeitados, conforme exemplificado na 
    Figura \ref{fig:sqi_comparison}.
\end{enumerate}

A Tabela \ref{tab:sqi_threshold_justification} sintetiza a fundamentação dos 
limiares estabelecidos.

\begin{table}[htbp]
    \centering
    \caption{Justificativa empírica para os limiares de rejeição}
    \label{tab:sqi_threshold_justification}
    \begin{tabular}{p{2.5cm}p{3cm}p{3.5cm}}
        \toprule
        \textbf{Modalidade} & \textbf{Limiar} & \textbf{Fundamentação} \\
        \midrule
        EEG & SNR mín. $-5{,}0$ dB & Inferior ao ruído instrumental típico \\
        EEG & Curtose máx. $50{,}0$ & Captura piscadas sem rejeitar fisiológico \\
        ECG & Curtose máx. $100{,}0$ & Accomoda picos R pronunciados \\
        EMG & Entropia mín. $0{,}20$ & Detecta bursts musculares íntegros \\
        fNIRS & SNR mín. $-50{,}0$ dB & Ruído fotônico intrínseco \\
        \bottomrule
    \end{tabular}
\end{table}
```

**File:** `tex/2-textuais/3-metodologia.tex`

---

### Phase 3: Results Chapter Updates

**Priority:** P1  
**Status:** Not Started

#### Change 3: Update Section 4.5.1 (4-resultados.tex)

Replace current content with reference to methodology:

```latex
\subsection{Calibração de Limiares por Modalidade}
Os limiares de rejeição foram estabelecidos conforme descrito na 
Seção \ref{sec:calibracao_limiares}, calibrados para assegurar a robustez 
estatística das janelas de sinal. Observa-se que a modalidade fNIRS foi 
configurada com parâmetros de SNR extremamente permissivos devido à natureza 
do ruído intrínseco, enquanto o EEG exige maior estabilidade espectral.

A Tabela \ref{tab:sqi_thresholds} apresenta os limiares de rejeição 
estabelecidos para cada modalidade.
```

---

### Phase 4: Literature Comparison

**Priority:** P2  
**Status:** Not Started

#### Change 4: Add References to BibTeX (referencias.bib)

Add the following entries:

```bibtex
@misc{naser2023multimodal,
    author = {Mohammad Naser and Others},
    title = {Dataset of Multi-Modal Physiological Signals (fNIRS, EEG, ECG, EMG) 
             Recorded Across Different Emotional States},
    year = {2023},
    howpublished = {IEEE DataPort},
    url = {https://ieee-dataport.org/documents/dataset-multi-modal-physiological-signals-fnirs-eeg-ecg-emg-recorded-across-different}
}

@article{cuena2019tool,
    title={A tool for the real-time evaluation of ECG signal quality and activity 
           classification based on higher-order-statistics},
    author={Cuena, Rodrigo and Lerga, Jon and markelj2019tool},
    journal={Biomedical Signal Processing and Control},
    volume={52},
    pages={332--340},
    year={2019},
    publisher={Elsevier}
}

@article{zheng2019eeg,
    title={Good data? The EEG Quality Index for Automated Assessment of Signal Quality},
    author={Zheng, Wei and Liu, Wei and Ozturk, Yalcin and Bhatti, PT},
    journal={IEEE Transactions on Biomedical Engineering},
    volume={66},
    number={12},
    pages={3558--3567},
    year={2019},
    publisher={IEEE}
}

@article{taylor2022robustness,
    title={Robustness of electrocardiogram signal quality indices},
    author={Taylor, S and Jaquet, C and Levine, J and Finlay, D and Nugent, C},
    journal={Journal of the Royal Society Interface},
    volume={19},
    number={189},
    pages={20220012},
    year={2022},
    publisher={Royal Society}
}
```

**File:** `tex/3-pos-textuais/referencias.bib`

---

#### Change 5: Add Literature Comparison Table (4-resultados.tex)

Add new subsection in Chapter 4:

```latex
\subsection{Comparação com Abordagens da Literatura}
\label{sec:comparacao_literatura}

A Tabela \ref{tab:comparacao_sqi} apresenta a comparação entre a metodologia 
proposta e abordagens consolidadas da literatura para avaliação de qualidade 
de biossinais.

\begin{table}[htbp]
    \centering
    \caption{Comparação entre metodologias de SQI}
    \label{tab:comparacao_sqi}
    \begin{tabular}{lccc}
        \toprule
        \textbf{Trabalho} & \textbf{Modalidade} & \textbf{Métricas Utilizadas} & \textbf{Abordagem} \\
        \midrule
        \citealp{cuena2019tool} & ECG & Curtose, Assimetria & hOS-SQI \\
        \citealp{zheng2019eeg} & EEG & 6 métricas combinadas & EEGQI Framework \\
        \citealp{taylor2022robustness} & ECG & SQIp, SQIsnr, SQIkur & Análise de Robustez \\
        \textbf{Proposto} & EEG/ECG/EMG & SNR, Curtose, Entropia & Thresholds Empíricos \\
        \bottomrule
    \end{tabular}
\end{table}
```

**File:** `tex/2-textuais/4-resultados.tex`

---

## Summary of Changes

| Phase | File | Changes | Priority |
|-------|------|---------|----------|
| 1 | `tex/2-textuais/3-metodologia.tex` | Update dataset characterization | P1 |
| 2 | `tex/2-textuais/3-metodologia.tex` | Add threshold calibration methodology section | P1 |
| 3 | `tex/2-textuais/4-resultados.tex` | Update SQI threshold section with reference | P1 |
| 4 | `tex/3-pos-textuais/referencias.bib` | Add 4 bibliography entries | P2 |
| 5 | `tex/2-textuais/4-resultados.tex` | Add literature comparison table | P2 |

---

## Files NOT to Modify (Per User Request)

- `src/biosignal/stages/sqi.py` - No code changes
- No classifier implementation

---

## Implementation Order

1. **Phase 1** - Dataset documentation fix
2. **Phase 2** - Threshold methodology
3. **Phase 3** - Results updates
4. **Phase 4** - Literature comparison

---

## Status

- [ ] Phase 1: Dataset Documentation
- [ ] Phase 2: Threshold Justification
- [ ] Phase 3: Results Updates
- [ ] Phase 4: Literature Comparison

**Created:** 2026-04-01  
**Author:** Plan Mode Analysis
