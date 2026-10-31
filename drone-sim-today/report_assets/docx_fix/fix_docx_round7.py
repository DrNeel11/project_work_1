# -*- coding: utf-8 -*-
"""Seventh pass: corrects the ten-seed statistics in Section 6.11 (the first version mixed two detectors) and adds the 31-wall ten-seed result."""
import os
import docx

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(os.path.dirname(os.path.dirname(HERE)), "UW-TIG_Project_Work_Report_final.docx")
d = docx.Document(DOC)


def set_text(prefix, text):
    for p in d.paragraphs:
        if p.text.startswith(prefix):
            p.runs[0].text = text
            for r in p.runs[1:]:
                r._r.getparent().remove(r._r)
            return
    raise KeyError(prefix)


set_text("Weight sensitivity.", "Weight sensitivity. Setting both weights to 0, 6 and 20 leaves F1 unchanged (oracle detector, static, uncertain and growing scenarios; "
         "9 walls: 0.918 in all three; 31 walls: 0.822, 0.821, 0.820). The terms do not change the route even when they dominate the score.")
set_text("Staleness and lookahead.", "Staleness and lookahead. Without them the flight is shorter (9 walls: 81 to 83 m against 125 m; 31 walls: 417 and 446 m against 481 m). "
         "With the real detector the confirmed F1 does not fall: on the 9-wall yard it is higher, 0.973 against 0.963 (paired +0.010 in favour of removing them, "
         "95% CI +0.003 to +0.017, all 10 seeds); on the 31-wall yard it is 0.925 and 0.920 against 0.921, a tie. With the oracle detector F1 falls slightly "
         "(31 walls 0.862 and 0.864 against 0.871). These two terms therefore cost flight, and in the 9-wall yard they cost a little detection quality as well.")
set_text("Ten seeds, 9-wall yard", "Ten seeds, original detector, confirmed F1 (seeds 0 to 9). 9-wall yard: UW-TIG 0.963 (95% CI 0.941 to 0.982) at 125 m; "
         "Alamdari 0.951 at 168 m; Rückin 0.938 at 206 m; GATSBI 0.914; random 0.891 at 379 m; Bircher 0.816; Isler 0.663; no coverage phase 0.679. "
         "UW-TIG minus Alamdari is +0.012 (CI +0.001 to +0.022, 6 of 10 seeds) and minus Rückin +0.025 (CI −0.002 to +0.055, 4 of 10): a small, borderline "
         "lead over Alamdari and not significant over Rückin. 31-wall yard: Alamdari 0.928 at 570 m; UW-TIG 0.921 (0.908 to 0.933) at 481 m; GATSBI 0.917 at 471 m; "
         "Rückin 0.906 at 846 m; random 0.827 at 2,396 m; Bircher 0.664; no coverage phase 0.658; Isler 0.474. UW-TIG is level with Alamdari (−0.007, CI −0.014 to 0.000) "
         "and GATSBI (+0.004, −0.005 to +0.013) and ahead of Rückin by +0.014 (+0.001 to +0.029) with 43% less flight. In both yards the no-uncertainty and no-growth "
         "variants differ from UW-TIG by 0.002 or less.")
set_text("Ten seeds were run on the 9-wall yard", "Ten seeds were run in each yard. That is enough to see the coverage effect, but UW-TIG is only level with the best rivals "
         "(Alamdari in both yards, GATSBI at 31 walls) and is not significantly ahead of Rückin in the 9-wall yard.")
d.save(DOC)
print("saved")
