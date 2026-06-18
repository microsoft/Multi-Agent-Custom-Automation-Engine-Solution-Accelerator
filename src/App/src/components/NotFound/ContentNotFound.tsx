import React from "react";
import {
  Button,
  Image,
  Text,
  Title2,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import NotFound from "../../assets/WebWarning.svg";

type ContentNotFoundProps = {
  imageSrc?: string;
  title?: string;
  subtitle?: string;
  primaryButtonText?: string;
  onPrimaryButtonClick?: () => void;
  secondaryButtonText?: string;
  onSecondaryButtonClick?: () => void;
};

const DEFAULT_IMAGE = NotFound;
const DEFAULT_TITLE = "";

const useStyles = makeStyles({
  root: {
    minHeight: "80vh",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    textAlign: "center",
    gap: tokens.spacingVerticalL,
    padding: tokens.spacingVerticalXXL,
  },
  image: {
    width: "80px",
    height: "80px",
    objectFit: "contain",
  },
  buttonGroup: {
    display: "flex",
    gap: tokens.spacingHorizontalM,
    justifyContent: "center",
    marginTop: tokens.spacingVerticalM,
  },
});

const ContentNotFound: React.FC<ContentNotFoundProps> = ({
  imageSrc = DEFAULT_IMAGE,
  title = DEFAULT_TITLE,
  subtitle,
  primaryButtonText,
  onPrimaryButtonClick,
  secondaryButtonText,
  onSecondaryButtonClick,
}) => {
  const styles = useStyles();

  return (
    <div className={styles.root}>
      <Image src={imageSrc} alt="Content Not Found" className={styles.image} />
      <Title2>{title}</Title2>
      {subtitle && (
        <Text style={{ color: "gray", fontSize: 16, fontFamily: "sans-serif" }}>
          {subtitle}
        </Text>
      )}
      {(primaryButtonText || secondaryButtonText) && (
        <div className={styles.buttonGroup}>
          {primaryButtonText && (
            <Button appearance="primary" onClick={onPrimaryButtonClick}>
              {primaryButtonText}
            </Button>
          )}
          {secondaryButtonText && (
            <Button appearance="outline" onClick={onSecondaryButtonClick}>
              {secondaryButtonText}
            </Button>
          )}
        </div>
      )}
    </div>
  );
};

export default ContentNotFound;
