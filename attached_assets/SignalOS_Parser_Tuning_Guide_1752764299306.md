# 🛠️ SignalOS AI Parser Fine-Tuning Guide

**Last Updated:** 2025-07-17  10:00

This guide helps you **finely tune** your multi-AI signal parser for **maximum accuracy** and **robustness**. It covers dataset management, model selection, training workflows, evaluation metrics, and deployment strategies.

---

## 1. 📚 Dataset Preparation

1. **Collect Raw Signals & Corrections**
   - Aggregate raw Telegram messages and corresponding parsed JSON (entry, SL, TPs).
   - Store in **JSONL**: each line contains {"raw": "...", "parsed": {...}}.
   - Include **edge cases**: images (OCR output), multilingual texts, unusual formats.

2. **Labeling & Cleaning**
   - Verify each sample for correct annotations.
   - Normalize numeric formats (e.g., pips, decimal places).
   - Remove duplicates and near-identical entries.

3. **Train/Test/Validation Split**
   - 80% for training, 10% validation, 10% testing.
   - Ensure distribution of providers/formats across splits.

---

## 2. 🤖 Model Selection & Architecture

1. **Primary LLM Parser**
   - Phi-3 Mini or Mistral 7B for structured JSON output.
   - Use prompt engineering patterns:
     ```
     Extract {pair, direction, entry, sl, tp} from signal: '{raw_text}'
     ```

2. **Secondary NLP Parser**
   - spaCy with custom NER for key fields.
   - Train on labeled tokens (PAIR, DIR, ENTRY, SL, TP).

3. **Fallback Regex Parser**
   - Robust regex patterns for purely textual extraction.

---

## 3. ⚙️ Training Workflow

1. **Fine-Tuning LLM (Optional)**
   - Use HuggingFace Transformers:
     ```
     transformers-cli fine-tune        --model phi-3-mini        --dataset path/to/train.jsonl        --output_dir models/phi3-finetuned        --task text2json        --batch_size 8        --epochs 3
     ```

2. **Training spaCy NER**
   - Convert JSONL to spaCy format and train:
     ```python
     import spacy
     from spacy.training import Example
     nlp = spacy.blank("en")
     ner = nlp.add_pipe("ner")
     # add labels and training examples
     ```

3. **Parameter Tuning**
   - Batch Size: 4–16
   - Learning Rate: 2e-5–5e-5
   - Epochs: 2–5
   - Prompt Variants: Test different templates, measure performance.

---

## 4. 📈 Evaluation Metrics

1. **Accuracy**: Percentage of fully correct parsed fields.
2. **Field-Level F1 Score**: For each entity (PAIR, ENTRY, SL, TP).
3. **Latency**: Average time per parse.
4. **Error Breakdown**: Missing fields, incorrect values, format mismatches.

---

## 5. 🔄 Continuous Retraining Loop

1. **Feedback Logging**
   - Log parser failures via feedback_logger.py.
   - Store corrections in data/feedback.jsonl.

2. **Scheduled Retraining**
   - Weekly or monthly batch jobs incorporate new samples.
   - CI/CD pipeline auto-trains and packages new model versions.

3. **A/B Testing**
   - Deploy v1.0 to subset A, v1.1 to subset B.
   - Compare parse accuracy and error rates.

---

## 6. 🚀 Deployment & Versioning

1. **Model Versioning**
   - Semantic versions: parser-v1.0, parser-v1.1.
   - Store under models/versions/.

2. **Auto Model Fetch**
   - model_manager.py checks version.json and downloads updates.
   - Verify integrity with checksum.

3. **Rollback Plan**
   - If performance drops, revert to previous stable version.

---

## 7. 🔧 Best Practices

- Keep prompts consistent; minor changes can shift output.
- Augment dataset with synthetic examples (punctuation, languages).
- Monitor real-world performance: track parse confidence vs corrections.
- Document prompt templates and regex patterns for traceability.

---

**By following this guide, your AI parser will become highly accurate, adaptable to new signal formats, and continuously improve over time.**
