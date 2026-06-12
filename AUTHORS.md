AWS S3 Lambda function for Coralogix is written and maintained by Coralogix Ltd. 

# Contributors  

* Coralogix Ltd. <[info@coralogix.com](mailto:info@coralogix.com)> [@coralogix](https://github.com/coralogix)

## Contribution Notes

For published lambda packages in `src/<name>/`:

- Keep `template.yaml` `SemanticVersion` and the top `CHANGELOG.md` entry in sync.
- Format the top changelog entry as `## [X.Y.Z] - YYYY-MM-DD` and include at least one bullet.
- Expect merged releases to publish a matching `<name>-v<X.Y.Z>` Git tag and GitHub Release automatically.
- Use the `skip-changelog` label only when the change does not need a changelog update or version bump.
