# AI/ML Module

## Objective

Provide academic-support analytics using historical academic information.

## Candidate Features

- Attendance percentage
- Previous semester percentage/CGPA
- Internal examination scores
- Assignment average
- Quiz average

## Target

A project may define a target such as:

- Low
- Moderate
- High

The target definition must be documented and validated against the dataset.

## Recommended Workflow

```text
Dataset
  ↓
Data Validation
  ↓
Cleaning
  ↓
Feature Engineering
  ↓
Train/Test Split
  ↓
Baseline Model
  ↓
Random Forest / Logistic Regression
  ↓
Evaluation
  ↓
Model Selection
  ↓
Save Model
  ↓
Django Integration
```

## Evaluation

For classification, consider:

- Accuracy
- Precision
- Recall
- F1-score
- Confusion matrix

Do not report only accuracy when classes are imbalanced.

## Responsible Use

Predictions are intended as support signals. They should not automatically determine grades, disciplinary action, admission, scholarships, or other high-impact outcomes.

Use anonymized/synthetic data in the GitHub repository unless you have explicit authorization to publish real institutional data.
